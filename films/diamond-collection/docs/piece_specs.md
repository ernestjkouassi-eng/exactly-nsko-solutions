# NSKO SOLUTIONS · Diamond Collection · piece specs (checkpoint 1)

Source photos are cleaned in `assets/clean/` (people, inset, phone UI and watermarks removed). Each piece below is read from those photos. Ernest confirmed these are **real NSKO pieces**, so pieces 1 to 3 are matched to the photos as closely as the photos allow. The watch stays an original NSKO design (brief).

## 1. Rose-gold iced Cuban link (IMG_9414, IMG_9412) + clasp (IMG_9407 jpg/png)
- **Chain type:** Miami Cuban, very wide (photo reads about 20 to 22 mm), heavy, double-thick curb links that interlock and lie flat.
- **Count:** about 34 to 38 links around a standard neck (the bust shows ~17 on the visible front half).
- **Metal:** 18k rose gold, visible only in the gaps and on the link sides. Base colour #F2B8A0, metallic 1, roughness 0.10.
- **Link face:** each link carries **two halo clusters** side by side. Each cluster is a **round brilliant centre (~4.5 mm)** with a **halo of 14 to 16 micro rounds (~1.1 mm)** in a raised bezel. Between clusters: pavé of micro rounds (~0.9 mm) filling the remaining face.
- **Link edges:** outer and inner edges also pavé-set (one row), so the chain reads fully iced from the side.
- **Clasp (box clasp):** oval/pear dome, larger than a link (about 1.8 links long).
  - **Centre:** a **large pear-shaped motif** made of pear-cut stones (one large pear centre, ~10 smaller pears radiating), framed by a **micro-pavé pear outline**.
  - **Around it:** 6 to 7 **pear-in-halo** and **round-in-halo** clusters, then a **domed pavé** shoulder.
  - **Underneath:** hidden box lock (tongue + box + safety latch). Not visible in photos; built from standard box-clasp anatomy.
- **Display:** soft grey velvet neck bust (light warm grey #C9C4C0), studio dark behind.
- **Stone count (approx.):** ~76 halo centres, ~1,150 halo stones, ~1,800 pavé stones, clasp ~400. Built with instancing.

## 2. Lady's yellow-diamond pendant necklace (IMG_9409, woman removed)
- **Chain:** white gold, **leaf/marquise cluster links**: each link is a small spray of 3 marquise-shaped leaves (2 angled, 1 forward) set with white stones. About 30 to 34 leaf units per side. Gets slightly larger toward the front.
- **Front:** the two sides meet in a **V**, joined by a slightly larger leaf cluster (5 leaves).
- **Drop:** short leaf segment, then the **yellow pear diamond pendant**. The photo shows the pear's point up toward the bail (rounded end at the bottom), so the model follows the photo. Pear about 14 x 10 mm. Canary yellow (#E9C24A body colour, transmission). **White diamond halo** of micro rounds around it. Small bail at the top.
- **Metal:** white gold / platinum (base #E3E5E8, metallic 1, roughness 0.12).

## 3. Marquise diamond ring (IMG_9410)
- **Centre stone:** large **marquise brilliant**, about 2.2 : 1 length to width. In the photo it covers most of the finger, so about 25 x 11 mm for the film's look (we will not state a carat weight).
- **Setting:** **6 claws**: one V-claw at each point, two pairs along the sides. Platinum.
- **Under-gallery:** open basket under the stone (visible in the cut-away).
- **Band:** platinum, **pavé shoulders** tapering into the band, **milgrain edge** (tiny beaded rim) on both band edges. Photo shows a twisted/beaded texture on the shank: milgrain plus a fine pavé row.
- **Metal:** platinum (#E3E5E8, roughness 0.10).

## 4. Celestial tourbillon watch: original NSKO design (style from IMG_9402 / IMG_9401, not a copy)
Kept from the reference's feel, redesigned layout:
- **Case:** 44 mm round, polished 18k rose gold, **open/skeleton case** with a **crescent window** cut through the bezel at 2 o'clock (ours: one asymmetric arc window, not their round opening).
- **Lugs:** short sculpted lugs, each set with **diamond baguettes** in rows (ours: 3 rows, stepped).
- **Dial ring:** outer ring of **blue sapphire baguettes** in two tiers (ours: tapered toward 6 o'clock).
- **Centre:** black open skeleton bridge; **flying tourbillon at 7 o'clock** with a rose-gold cage (ours: 3-arm cage with the NSKO N cut-out in the upper bridge).
- **Planets:** 6 small gemstone spheres on thin rose-gold arms, orbiting the centre: amethyst, citrine/orange, peridot, blue topaz, a blue-and-gold Earth, a banded agate. (Ours: different count, positions and colours from the reference.)
- **Time:** small off-centre sub-dial at 1 o'clock in deep blue with rose-gold hands. **No zodiac signs, no text.**
- **Crystal:** domed sapphire crystal.
- **Strap:** deep blue alligator-style leather, rose-gold buckle.
- **Branding:** tiny "NSKO" engraved on the caseband at 9 o'clock only. Nothing else.

## Materials (all pieces)
- Diamond: IOR 2.417, dispersion on (spectral split R 2.407 / G 2.417 / B 2.451), roughness 0, real brilliant/pear/marquise/baguette cuts as faceted meshes (not spheres).
- Yellow diamond: same cut and IOR, volume absorption tinted canary.
- Sapphire (blue baguettes): IOR 1.77, blue absorption. Gem planets: correct IOR per stone (amethyst 1.54, citrine 1.54, peridot 1.65, topaz 1.62).
- Rose gold #F2B8A0, white gold/platinum #E3E5E8, metallic 1, roughness 0.08 to 0.15.

## Open points for Ernest
1. End-card line: "Lab-grown diamond craftsmanship"? Only if true. Otherwise "Fine jewellery by NSKO".
2. Are these real NSKO pieces? If they are concepts, the film should not imply they are for sale. A small "Concept" or "CGI" note can sit in the post caption instead of the film.

## Build notes (checkpoint 2)
- Blender files are generated by code: `blender/cuban.py`, `necklace.py`, `ring.py`, `watch.py` (+ `*_still.py` for the lighting stills). Shared cuts, materials and studio in `jlib.py`.
- Every stone sits on an **open gallery** (rims, baskets, claws), never buried in metal, so light reflects back out of the pavilion as in a real setting.
- Studio lights are linked to the jewellery only (Blender light linking): the velvet stays moody while the stones get crisp white flashes. No glow, flare or sparkle overlays.
- Cuban: 32 links, 2 halo clusters per link (5 mm centre + 15 x 1.4 mm halo), pavé fill and edge rows, about 3,150 stones. Box clasp with raised pear motif (1 large pear + 10 pears + micro-pavé outline), 6 halo clusters, pavé dome, hidden box lock modelled for the explode.
- Necklace: 68 leaf units (2 marquises + a round), 5-marquise spray at the V, 2-unit drop, bail, 16 mm canary pear in a micro-pavé halo. Platinum.
- Ring: 25 mm marquise, 6 claws, open two-rail basket, channel pavé shoulders, milgrain on both rails. Platinum.
- Watch: see `stills/watch_design_*.png`. 44 mm rose-gold case with an arc window scooped through the bezel at 2, aventurine "night sky" floor, two tiers of tapered blue sapphire baguettes (narrower toward 6), three dark skeleton bridges, flying tourbillon at 7 whose upper bridge is the NSKO "N", blue sub-dial at 1 with dot indices only, six gem planets (amethyst, citrine, peridot, blue topaz, blue-and-gold Earth, banded agate), domed AR-coated sapphire crystal, stepped baguette lugs, blue leather strap. Only text: "NSKO" engraved on the caseband at 9.
