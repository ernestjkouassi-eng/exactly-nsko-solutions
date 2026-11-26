// A3 print PDF: one page, the 300 dpi render placed edge to edge (keeps the tilted Trade Card sharp; Chromium rasterises 3D transforms at low resolution in PDF).
const { chromium } = require('playwright'); const path = require('path'); const fs = require('fs');
(async () => {
  const b = await chromium.launch({ args: ['--disable-gpu'] }); const pg = await b.newPage();
  const img = 'data:image/png;base64,' + fs.readFileSync(path.join(__dirname, 'out/nsko-quant-poster-A3-300dpi.png')).toString('base64');
  await pg.setContent(`<html><head><title>NSKO QUANT A3 poster</title><style>@page{size:297mm 420mm;margin:0}html,body{margin:0;background:#08080F}img{display:block;width:297mm;height:420mm}</style></head><body><img src="${img}"></body></html>`);
  await pg.pdf({ path: path.join(__dirname, 'out/nsko-quant-poster-A3.pdf'), width: '297mm', height: '420mm', printBackground: true });
  await b.close(); console.log('pdf ok');
})();
