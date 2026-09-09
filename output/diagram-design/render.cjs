const {chromium} = require('/Users/rocket/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/playwright');
const path = require('path');
const fs = require('fs');
const outDir = process.argv.includes('--editorial') ? path.join(__dirname,'editorial') : __dirname;
(async()=>{
  const browser = await chromium.launch({headless:true});
  const page = await browser.newPage({viewport:{width:1280,height:720},deviceScaleFactor:2});
  const report=[];
  for(const name of ['01-architecture','02-extraction','03-participation','04-implementation']){
    await page.goto('file://'+path.join(outDir,name+'.html'));
    await page.evaluate(()=>document.fonts.ready);
    const issues=await page.evaluate(()=>{
      const texts=[...document.querySelectorAll('svg text')];
      const boxes=texts.map(t=>({text:t.textContent,b:t.getBBox()}));
      const errors=[];
      for(const {text,b} of boxes)if(b.x<0||b.y<0||b.x+b.width>1280||b.y+b.height>720)errors.push('outside: '+text);
      for(let i=0;i<boxes.length;i++)for(let j=i+1;j<boxes.length;j++){
        const a=boxes[i].b,b=boxes[j].b;
        if(a.x<b.x+b.width&&a.x+a.width>b.x&&a.y<b.y+b.height&&a.y+a.height>b.y)errors.push('overlap: '+boxes[i].text+' / '+boxes[j].text);
      }
      return errors;
    });
    await page.locator('svg').screenshot({path:path.join(outDir,name+'.png')});
    report.push({name,issues});
  }
  fs.writeFileSync(path.join(outDir,'validation.json'),JSON.stringify(report,null,2));
  console.log(JSON.stringify(report,null,2));
  await browser.close();
})();
