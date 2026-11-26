"""FastAPI app: REST + the /ws event bus. Bound to 127.0.0.1:8787 only.

Security on localhost:
- CORS allows only the desktop app origins.
- Every POST must carry the header `X-NSQ-Client` (browsers cannot add it cross-site without a CORS
  pre-flight we refuse), which blocks drive-by requests from web pages.
- Sensitive endpoints need `Authorization: Bearer <session token>` from /account/login.
- /kill needs X-NSQ-Client but NOT a login, so it always works.
"""
from __future__ import annotations

import asyncio
import base64
import contextlib
import json

from fastapi import Depends, FastAPI, Header, HTTPException, Request, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, Response
from pydantic import BaseModel

from . import __version__, account, bus, health, licence, vault
from .audit import tail as audit_tail, verify_chain
from .brokers import BrokerError, active, build, catalogue, set_active
from .db import conn
from .settings import all_settings, get, set as sset

ORIGINS = ["tauri://localhost", "http://tauri.localhost", "https://tauri.localhost", "http://localhost:5173",
           "http://127.0.0.1:5173", "http://localhost:4173"]


@contextlib.asynccontextmanager
async def lifespan(app: FastAPI):
    from .engine import engine
    if app.state.start_engine:
        engine.start()
    yield
    if app.state.start_engine:
        engine.stop()


def create_app(start_engine: bool = True) -> FastAPI:
    app = FastAPI(title="NSKO QUANT engine", version=__version__, lifespan=lifespan)
    app.state.start_engine = start_engine
    app.add_middleware(CORSMiddleware, allow_origins=ORIGINS, allow_methods=["GET", "POST"],
                       allow_headers=["Authorization", "Content-Type", "X-NSQ-Client"])

    @app.middleware("http")
    async def csrf_guard(request: Request, call_next):
        if request.method == "POST" and not request.headers.get("x-nsq-client"):
            return JSONResponse({"detail": "missing X-NSQ-Client header"}, status_code=403)
        return await call_next(request)

    for mod in ("nsq.data.api", "nsq.research.api", "nsq.lab.api", "nsq.godseye.api"):
        try:
            import importlib
            app.include_router(importlib.import_module(mod).router)
        except Exception:
            pass
    _routes(app)
    return app


def need_session(authorization: str | None = Header(default=None)) -> account.Session:
    tok = (authorization or "").removeprefix("Bearer ").strip()
    s = account.session(tok)
    if not s:
        raise HTTPException(401, "Sign in first.")
    return s


def _err(e: account.AccountError, status: int = 400):
    raise HTTPException(status, {"code": e.code, "message": e.msg})


class CreateBody(BaseModel):
    email: str
    password: str
    name: str = ""
    pin: str | None = None


class LoginBody(BaseModel):
    email: str
    password: str
    totp: str | None = None


class RecoverBody(BaseModel):
    recovery_code: str
    new_password: str


class CodeBody(BaseModel):
    code: str


class PinBody(BaseModel):
    pin: str | None = None


class LicenceBody(BaseModel):
    key: str
    save: bool = True


class ApproveBody(BaseModel):
    plan_id: str
    decision: str = "approve"


class PhraseBody(BaseModel):
    phrase: str


class SettingBody(BaseModel):
    key: str
    value: object


class BrokerBody(BaseModel):
    name: str
    keys: dict[str, str] = {}
    live: bool = False


class SecretBody(BaseModel):
    value: str


class PassBody(BaseModel):
    passphrase: str
    data_b64: str | None = None


class PromoteBody(BaseModel):
    to: str
    version: int | None = None


class PackBody(BaseModel):
    pack: str


class KillBody(BaseModel):
    reason: str = "kill switch pressed"


PROTECTED_SETTINGS = {"mode", "live.unlocked_at", "trading.locked", "licence.key"}


def _routes(app: FastAPI) -> None:
    # ------------------------------------------------------------------ health + bus
    @app.get("/health")
    def get_health():
        from .connectivity import is_online
        from .trading.killswitch import is_locked
        return {**health.snapshot(), "version": __version__, "mode": get("mode"), "broker": active().name,
                "online": is_online(), "locked": is_locked()[0], "demo": bool(get("demo")), "vault": vault.backend()}

    @app.websocket("/ws")
    async def ws(sock: WebSocket):
        origin = sock.headers.get("origin")
        if origin and origin not in ORIGINS:
            await sock.close(code=1008)
            return
        await sock.accept()
        loop = asyncio.get_running_loop()
        q: asyncio.Queue = asyncio.Queue(maxsize=5000)

        def push(ev: dict) -> None:
            def _put():
                if q.full():
                    with contextlib.suppress(Exception):
                        q.get_nowait()
                q.put_nowait(ev)
            with contextlib.suppress(RuntimeError):
                loop.call_soon_threadsafe(_put)

        unsub = bus.subscribe(push)
        try:
            await sock.send_text(json.dumps({"type": "engine_health", "ts": health.snapshot()["heartbeat"] or 0,
                                             "payload": health.snapshot()}, default=str))
            while True:
                ev = await q.get()
                await sock.send_text(json.dumps(ev, default=str))
        except (WebSocketDisconnect, RuntimeError):
            pass
        finally:
            unsub()

    # ------------------------------------------------------------------ account
    @app.post("/account/create")
    def acc_create(b: CreateBody):
        try:
            return account.create(b.email, b.password, b.name, b.pin)
        except account.AccountError as e:
            _err(e, 409 if e.code == "exists" else 400)

    @app.post("/account/login")
    def acc_login(b: LoginBody):
        try:
            return account.login(b.email, b.password, b.totp)
        except account.AccountError as e:
            _err(e, 401 if e.code in ("wrong_password", "wrong_totp", "totp_required") else 429 if e.code == "locked" else 400)

    @app.post("/account/recover")
    def acc_recover(b: RecoverBody):
        try:
            return account.recover(b.recovery_code, b.new_password)
        except account.AccountError as e:
            _err(e, 401)

    @app.get("/account")
    def acc_profile():
        return {"exists": account.exists(), "profile": account.profile()}

    @app.post("/account/pin/verify")
    def pin_verify(b: PinBody):
        try:
            return {"ok": account.verify_pin(b.pin or "")}
        except account.AccountError as e:
            _err(e, 429)

    @app.post("/account/pin")
    def pin_set(b: PinBody, s=Depends(need_session)):
        try:
            account.set_pin(s, b.pin)
        except account.AccountError as e:
            _err(e)
        return {"ok": True}

    @app.post("/account/totp/begin")
    def totp_begin(s=Depends(need_session)):
        return account.totp_begin(s)

    @app.post("/account/totp/confirm")
    def totp_confirm(b: CodeBody, s=Depends(need_session)):
        return {"ok": account.totp_confirm(s, b.code)}

    # ------------------------------------------------------------------ licence
    @app.post("/licence/check")
    def lic_check(b: LicenceBody):
        r = licence.check(b.key)
        if r["status"] == "valid" and b.save:
            sset("licence.key", b.key.strip())
        return r

    @app.get("/licence/check")
    def lic_status():
        return licence.check(get("licence.key", "") or "")

    # ------------------------------------------------------------------ trading control
    @app.post("/kill")
    def kill(b: KillBody | None = None):
        from .trading.killswitch import kill as do_kill
        return do_kill("api", (b.reason if b else "kill switch pressed"))

    @app.post("/trading/enable")
    def trading_enable(s=Depends(need_session)):
        from .trading.killswitch import enable
        return enable(s.email)

    @app.post("/trade/approve")
    def trade_approve(b: ApproveBody, s=Depends(need_session)):
        from .trading.flow import approve
        if b.decision not in ("approve", "skip"):
            raise HTTPException(400, "decision is approve or skip")
        if not approve(b.plan_id, b.decision):
            raise HTTPException(404, "No trade is waiting with that id (it may have timed out and been skipped).")
        return {"ok": True}

    @app.get("/trade/pending")
    def trade_pending():
        from .trading.flow import pending_approvals
        return {"pending": pending_approvals()}

    @app.get("/live/checklist")
    def live_checklist():
        from .trading.live_unlock import checklist
        return checklist()

    @app.post("/live/unlock")
    def live_unlock(b: PhraseBody, s=Depends(need_session)):
        from .trading.live_unlock import unlock
        return unlock(b.phrase, actor=s.email)

    @app.post("/mode/paper")
    def mode_paper(s=Depends(need_session)):
        from .trading.live_unlock import back_to_paper
        back_to_paper(s.email)
        return {"mode": "paper"}

    # ------------------------------------------------------------------ brokers
    @app.get("/brokers")
    def brokers():
        return {"active": active().name, "brokers": catalogue()}

    @app.post("/brokers/connect")
    def broker_connect(b: BrokerBody, s=Depends(need_session)):
        for k, v in b.keys.items():
            vault.put(f"{b.name}.{k}", v)
            vault.remember_name(f"{b.name}.{k}")
        try:
            br = build(b.name, live=b.live)
            br.connect()
            perms = br.permissions()
        except BrokerError as e:
            raise HTTPException(400, str(e))
        if perms.get("withdrawals") is True:
            raise HTTPException(400, "This API key can withdraw money. Make a new key with trading permission only.")
        set_active(br)
        from .engine import engine
        if engine.flow:
            from .trading.flow import TradeFlow
            engine.flow = TradeFlow(br)
        from .demo import source
        source.stop()
        sset("broker", b.name)
        from .audit import audit
        audit(s.email, "broker.connect", {"broker": b.name, "permissions": perms})
        from .recovery import reconcile
        return {"ok": True, "broker": b.name, "permissions": perms, "reconcile": reconcile(br)}

    @app.get("/brokers/permissions")
    def broker_perms():
        try:
            return {"broker": active().name, **active().permissions()}
        except BrokerError as e:
            raise HTTPException(400, str(e))

    @app.get("/withdraw/helper")
    def withdraw_helper():
        from .trading.withdraw import helper
        return helper()

    @app.get("/account/summary")
    def acct_summary():
        b = active()
        a = b.account()
        return {"account": a.dict(), "positions": [p.dict() for p in b.positions()], "orders": [o.dict() for o in b.orders()],
                "paper": b.name == "paper", "demo": False}

    # ------------------------------------------------------------------ vault (write-only)
    @app.post("/vault/{name}")
    def vault_put(name: str, b: SecretBody, s=Depends(need_session)):
        where = vault.put(name, b.value)
        vault.remember_name(name)
        return {"ok": True, "stored_in": where}

    @app.get("/vault")
    def vault_names():
        return {"backend": vault.backend(), "names": vault.names()}

    # ------------------------------------------------------------------ settings
    @app.get("/settings")
    def settings_all():
        return {k: v for k, v in all_settings().items() if not k.startswith(("vault.", "licence.key", "strategy.pending"))}

    @app.post("/settings")
    def settings_set(b: SettingBody, s=Depends(need_session)):
        if b.key in PROTECTED_SETTINGS:
            raise HTTPException(400, f"{b.key} cannot be set here")
        if b.key == "risk.gate_enabled" and not b.value and get("mode") == "live":
            raise HTTPException(400, "The risk gate cannot be switched off in live mode.")
        sset(b.key, b.value)
        from .audit import audit
        audit(s.email, "settings.set", {"key": b.key, "value": b.value})
        return {"ok": True}

    # ------------------------------------------------------------------ backup
    @app.post("/backup/export")
    def backup_export(b: PassBody, s=Depends(need_session)):
        from .backup import export
        return Response(export(b.passphrase), media_type="application/octet-stream",
                        headers={"Content-Disposition": 'attachment; filename="my-desk.nsko"'})

    @app.post("/backup/restore")
    def backup_restore(b: PassBody, s=Depends(need_session)):
        from .backup import restore
        try:
            return restore(base64.b64decode(b.data_b64 or ""), b.passphrase)
        except ValueError as e:
            raise HTTPException(400, str(e))

    # ------------------------------------------------------------------ audit + risk
    @app.get("/audit/verify")
    def audit_verify():
        return verify_chain()

    @app.get("/audit")
    def audit_list(n: int = 50):
        return {"entries": audit_tail(min(n, 500))}

    @app.get("/risk/events")
    def risk_events(n: int = 100):
        return {"events": conn().execute("SELECT * FROM risk_events ORDER BY id DESC LIMIT ?", (min(n, 1000),)).fetchall()}

    @app.get("/journal")
    def journal(n: int = 100):
        return {"trades": conn().execute("SELECT * FROM journal ORDER BY id DESC LIMIT ?", (min(n, 1000),)).fetchall()}

    # ------------------------------------------------------------------ strategies
    @app.get("/strategies")
    def strategies():
        return {"strategies": conn().execute("SELECT * FROM strategies ORDER BY updated_at DESC").fetchall()}

    @app.get("/strategies/{sid}/versions")
    def strategy_versions(sid: str):
        from .trading.strategies import versions
        return {"versions": versions(sid)}

    @app.post("/strategies/{sid}/promote")
    def strategy_promote(sid: str, b: PromoteBody, s=Depends(need_session)):
        from .trading.strategies import StrategyError, promote
        if b.to == "live":
            from .trading.live_unlock import is_unlocked
            if not is_unlocked():
                raise HTTPException(400, "Live is locked. Finish the live checklist first.")
        try:
            return promote(sid, b.to, b.version, actor=s.email)
        except StrategyError as e:
            raise HTTPException(400, str(e))

    @app.post("/strategies/{sid}/rollback")
    def strategy_rollback(sid: str, s=Depends(need_session)):
        from .trading.strategies import StrategyError, rollback
        try:
            return rollback(sid, actor=s.email)
        except StrategyError as e:
            raise HTTPException(400, str(e))

    @app.post("/strategies/pack")
    def strategy_pack(b: PackBody, s=Depends(need_session)):
        from .trading.strategies import StrategyError, install_pack
        try:
            return {"installed": install_pack(b.pack), "where": "lab"}
        except StrategyError as e:
            raise HTTPException(400, str(e))

    @app.post("/telegram/pair")
    def telegram_pair(b: CodeBody, s=Depends(need_session)):
        sset("notify.telegram_chat_id", b.code.strip())
        return {"ok": True}


app = create_app()
