(function(root){
'use strict';
const segmenter=new Intl.Segmenter('th',{granularity:'word'});
const words=text=>[...segmenter.segment(text.normalize('NFC').toLowerCase())].filter(x=>x.isWordLike).map(x=>x.segment);
const O='(?<o>ห[งญนมยรลว]|อย|[กขคตปพผบฟดท][รลว]|[สศซจ]ร|ส[ตปมกน]|[ก-ฮ])', F='(?<c>[ก-ฮ])?';
const codaGroups={k:'กขคฆ',t:'ดจชซฎฏฐฑฒตถทธศษส',p:'บปพฟภ',ng:'ง',n:'นณญรลฬ',m:'ม',y:'ย',w:'ว'};
const onsetGroups={k:'ก',kh:'ขฃคฅฆ',ng:'ง',ch:'ฉชฌ',c:'จ',s:'ซศษส',y:'ญย',d:'ฎด',t:'ฏต',th:'ฐฑฒถทธ',n:'ณน',b:'บ',p:'ป',ph:'ผพภ',f:'ฝฟ',m:'ม',r:'ร',l:'ลฬ',w:'ว',h:'หฮ',zero:'อ'};
const group=(char,groups)=>Object.keys(groups).find(k=>groups[k].includes(char))||null;
const rules=[
 ['เ'+O+'ีย'+F,'ia','long'],['เ'+O+'ือ'+F,'uea','long'],[O+'ัว'+F,'ua','long'],[O+'ว(?<c>[ก-ฮ])','ua','long'],
 ['เ'+O+'า','a','short','w'],['[ใไ]'+O+'ย','a','short','y'],['[ใไ]'+O,'a','short','y'],[O+'ำ','a','short','m'],
 [O+'รร(?<c>[ก-ฮ])','a','short'],[O+'รร','a','short','n'],
 ['เ'+O+'อะ','oe','short'],['เ'+O+'อ'+F,'oe','long'],['เ'+O+'ิ(?<c>[ก-ฮ])','oe','long'],['เ'+O+'ย','oe','long','y'],
 ['เ'+O+'็'+F,'e','short'],['เ'+O+'ะ','e','short'],['เ'+O+F,'e','long'],
 ['แ'+O+'็'+F,'ae','short'],['แ'+O+'ะ','ae','short'],['แ'+O+F,'ae','long'],
 ['โ'+O+'ะ','o','short'],['โ'+O+F,'o','long'],['เ'+O+'าะ','aw','short'],[O+'็อ'+F,'aw','short'],[O+'อ'+F,'aw','long'],
 [O+'ั'+F,'a','short'],[O+'ะ','a','short'],[O+'า'+F,'a','long'],
 [O+'ิ'+F,'i','short'],[O+'ี'+F,'i','long'],[O+'ึ'+F,'ue','short'],[O+'ือ','ue','long'],[O+'ื(?<c>[ก-ฮ])','ue','long'],
 [O+'ุ'+F,'u','short'],[O+'ู'+F,'u','long'],[O+'็'+F,'o','short'],[O+'(?<c>[ก-ฮ])','o','short'],
 ['(?<o>ฤ)ๅ','ue','long'],['(?<o>ฤ)','ue','short']
].map(([pattern,vowel,length,forced])=>({re:new RegExp('^'+pattern+'$'),vowel,length,forced}));
const exceptions={'ก็':['aw','short','','k'],'บ่':['aw','short','','b'],'เธอ':['oe','long','','th'],'ทราย':['a','long','y','s'],'ทราบ':['a','long','p','s'],'ทรง':['o','short','ng','s'],'ทรัพย์':['a','short','p','s'],'ทรวง':['ua','long','ng','s'],'ทราม':['a','long','m','s'],'แทรก':['ae','long','k','s'],'ทรุด':['u','short','t','s'],'โทรม':['o','long','m','s'],'จริง':['i','short','ng','c'],'ไซร้':['a','short','y','s'],'รัก':['a','short','k','r'],'ฉัน':['a','short','n','ch'],'ฝัน':['a','short','n','f'],'กัน':['a','short','n','k'],'วัน':['a','short','n','w'],'เงิน':['oe','long','n','ng'],'เดิน':['oe','long','n','d'],'เกิน':['oe','long','n','k'],'เป็น':['e','short','n','p'],'เพชร':['e','short','t','ph'],'เหตุ':['e','long','t','h'],'ชาติ':['a','long','t','ch'],'รถ':['o','short','t','r'],'กล':['o','short','n','k'],'คน':['o','short','n','kh'],'ผล':['o','short','n','ph'],'ไทย':['a','short','y','th'],'ฤดู':['ue','short','','r'],'ฤทัย':['ue','short','','r'],'กะ':['a','short','','k'],'บ้อ':['aw','short','','b'],'น้อ':['aw','long','','n'],'เด้อ':['oe','long','','d'],'เด้':['e','long','','d'],'ฮู้':['u','long','','h'],'คึด':['ue','short','t','kh'],'ถืก':['ue','long','k','th'],'เพิ่น':['oe','long','n','ph'],'เบิ่ด':['oe','short','t','b'],'เว่า':['a','short','w','w'],'ซ่อย':['aw','long','y','s'],'แซ่บ':['ae','long','p','s'],'เปิ้น':['oe','long','n','p'],'ปิ๊ก':['i','short','k','p'],'แต๊':['ae','long','','t'],'หรอย':['aw','long','y','r'],'พรือ':['ue','long','','ph-r'],'หม้าย':['a','long','y','m'],'หนัด':['a','short','t','n'],'ป๊อป':['aw','short','p','p'],'สต็อป':['aw','short','p','s-t'],'สไตล์':['a','short','y','s-t'],'สไมล์':['a','short','y','s-m'],'เทรนด์':['e','short','n','th-r'],'สเปซ':['e','long','t','s-p'],'ดริ้งก์':['i','short','ng','d-r'],'แทร็ป':['ae','short','p','th-r'],'แร็ป':['ae','short','p','r'],'ฟีล':['i','long','n','f'],'กรูฟ':['u','long','p','k-r']};
const extraLexicon=new Set(['บ่','ฮู้','ใด๋','ไผ','เด้อ','เด้','น้อ','คึด','ฮอด','ถืก','เพิ่น','ถิ่ม','ฮ้อ','บ้อ','ถ่า','เอิ้น','เบิ่ด','เว่า','ซ่อย','ส่อย','เมือ','แซ่บ','เบิ่ง','แม่น','มัก','เฮ็ด','จั่ง','จัง','ส่ำ','ซำ','ตั๋ว','ปาน','สิ','แหน่','พ้อ','มื้อ','หยัง','ข่อย','เซา','ย่าน','ม่วน','คัก','อ้าย','ฮัก','เฮา','เปิ้น','กิ๋น','แอ่ว','อู้','ปิ๊ก','เน้อ','แต๊','ใจ๋','ไป๋','ไผ๋','หรอย','แหลง','พรือ','หม้าย','หนัด','หิด','ไหร','เทือน','ไทย','ทรง','สร้าง','เศร้า','สร้อย','เสร็จ','ศรี','จริง','ไซร้','ทรัพย์','จันทร์','ศาสตร์','วรรค','วรรค์','ธรรม','กรรม','พรรค','สไตล์','สไมล์','ป๊อป','สต็อป','ดรอป','บล็อก','ล็อก','ช็อก','ร็อก','เทรนด์','เฟรนด์','แบรนด์','แกรนด์','สเปซ','เพลส','ดริ้งก์','แบงก์','แทร็ป','แร็ป','ฟีล','ชิล','มูฟ','กรูฟ','พรูฟ','เคลียร์','เชียร์','เบียร์','เกียร์','ทัวร์','ชัวร์','เวอร์','เว่อร์','เบลอ','เทิร์น','เบิร์น','เวิร์ก','เซิร์ฟ','การ์ด','ชาร์จ','มาร์ก','พาร์ต','สตาร์ต','สมาร์ต','แมตช์','เซนส์','เอนด์','เท็กซ์','เน็กซ์','ฟิกซ์','มิกซ์','ไวบ์','ไลฟ์','ไทม์','ไนท์','ไรท์','ไฟล์','ไลน์','เซ็ต','เน็ต','เจ็ต','เป๊ะ','อัพ','คัพ','คลับ','ผับ','ซับ']);
const leadCons=/^[กขคจฉชตถทปผพฝมศสอ]$/;
const soundCache=new Map(),syllableCache=new Map();let dictionary=new Set();
function leadSound(ch){const onset=group(ch,onsetGroups)||'zero';return {vowel:'a',length:'short',coda:'',onset,key:'a:short:',near:'a:'};}
function sound(text){
 if(soundCache.has(text))return soundCache.get(text);
 const rawNorm=text.replace(/เเ/g,'แ').replace(/\u0E4D\u0E32/g,'ำ');
 const clean=rawNorm.replace(/[่้๊๋]/g,'').replace(/(?:ทร|ตร|ดร|กษ|ษณ|ทย|รย)์/g,'').replace(/[ก-ฮ][ิุี]?์/g,'').replace(/((?:[เแโ][ก-ฮ]|[ก-ฮ][าีูั])[ก-ฮ])[ิุ]$/,'$1');let result=null;
 if(exceptions[rawNorm]||exceptions[clean]){const [vowel,length,coda,onset]=exceptions[rawNorm]||exceptions[clean];result={vowel,length,coda,onset};}
 else if(/^[ก-๛]+$/.test(clean)){for(const rule of rules){const match=clean.match(rule.re);if(!match)continue;let onset=match.groups.o;if(/^ห[งญนมยรลว]$/.test(onset))onset=onset.slice(1);else if(onset==='อย')onset='ย';else if(/^[สศซ]ร$/.test(onset))onset='ซ';else if(onset==='จร')onset='จ';else if(onset==='ฤ')onset='ร';const initial=group(onset[0],onsetGroups);result={vowel:rule.vowel,length:rule.length,coda:rule.forced||group(match.groups.c||' ',codaGroups)||'',onset:initial+(onset.length>1?'-'+onset.slice(1):'')};break;}}
 if(result){result.key=[result.vowel,result.length,result.coda].join(':');result.near=[result.vowel,result.coda].join(':');}
 soundCache.set(text,result);return result;
}
function setDictionary(list){dictionary=new Set([...list,...extraLexicon].filter(s=>sound(s)));syllableCache.clear();}
function syllables(word){
 if(syllableCache.has(word))return syllableCache.get(word);
 if(!/^[ก-๛]+$/.test(word)){const out=[{text:word,known:false}];syllableCache.set(word,out);return out;}
 const n=word.length,dp=Array(n+1).fill(null);dp[n]={cost:0,parts:[]};
 for(let i=n-1;i>=0;i--){
  for(let end=i+1;end<=Math.min(n,i+16);end++){
   if(!dp[end]||/[ะัาำิีึืุู็่้๊๋์]/.test(word[end]||'!'))continue;
   if(word.slice(end,end+2)==='รร')continue;
   const part=word.slice(i,end),valid=!!sound(part),inDictionary=dictionary.has(part)||!!exceptions[part.replace(/เเ/g,'แ').replace(/[่้๊๋]/g,'')];
   const isLead=end===i+1&&end<n&&leadCons.test(part)&&dp[end].parts[0]?.known;
   if(!valid&&!inDictionary&&!isLead&&end!==n)continue;
   const known=isLead||(valid&&(inDictionary||part.length>=2));
   const cost=(isLead?4:valid?(inDictionary?1:3):30+part.length)+dp[end].cost;
   if(!dp[i]||cost<dp[i].cost)dp[i]={cost,parts:[{text:part,known,lead:isLead},...dp[end].parts]};
  }
 }
 const result=dp[0]?.parts||[{text:word,known:false}];syllableCache.set(word,result);return result;
}
const names={vowel:'สัมผัสสระ',onset:'สัมผัสอักษร',coda:'เสียงตัวสะกดซ้ำ',assonance:'เสียงสระซ้ำ',near:'สัมผัสใกล้เคียง',repeat:'คำ/พยางค์ซ้ำ',multi:'สัมผัสหลายพยางค์',phrase:'วรรคซ้ำ'};
const pairKey=(type,a,b,scope='inner')=>'r:'+type+':'+scope+':'+[a,b].sort().join('|');
const bucket=n=>n===0?'none':n<.05?'low':n<.2?'mid':'high';
function analyze(text){
 const lines=[],units=[],tokens=[],edges=[],features=[],sections=[];let section=-1,nextSection=true;
 for(const [index,raw] of text.normalize('NFC').split(/\r?\n/).entries()){
  const heading=raw.match(/^\s*\[([^\]]+)\]\s*$/);
  if(!raw.trim()||heading){nextSection=true;if(heading)sections.push({after:lines.length,title:heading[1]});continue;}
  if(nextSection){section++;nextSection=false;}
  const line={index:lines.length,number:index+1,section,raw,units:[],words:[],scheme:'?'};
  for(const item of segmenter.segment(raw.toLowerCase())){if(!item.isWordLike)continue;tokens.push(item.segment);line.words.push(item.segment);features.push('w:'+item.segment);let localOffset=item.index;
   for(const part of syllables(item.segment)){const u={id:units.length,text:part.text,word:item.segment,line:line.index,lineNumber:line.number,position:line.units.length+1,start:localOffset,end:localOffset+part.text.length,known:part.known,sound:part.lead?leadSound(part.text):(part.known?sound(part.text):null)};line.units.push(u);units.push(u);localOffset=u.end;}
  }
  if(line.units.length)lines.push(line);
 }
 const edgeKeys=new Set();
 function add(type,a,b,scope,extra={}){if(a.id===b.id)return;const key=[type,Math.min(a.id,b.id),Math.max(a.id,b.id),extra.size||''].join(':');if(edgeKeys.has(key))return;edgeKeys.add(key);edges.push({id:edges.length,type,a:a.id,b:b.id,scope,...extra});features.push(pairKey(type,a.text,b.text,scope));}
 function compare(a,b,scope,all=true){
  if(a.text===b.text){add('repeat',a,b,scope);return;}
  const x=a.sound,y=b.sound;if(!x||!y)return;
  if(x.key===y.key)add('vowel',a,b,scope);
  else if(x.near===y.near)add('near',a,b,scope);
  else if(all&&x.vowel===y.vowel&&x.length===y.length)add('assonance',a,b,scope);
  if(all&&x.onset===y.onset)add('onset',a,b,scope);
  if(all&&x.coda&&x.coda===y.coda&&x.key!==y.key)add('coda',a,b,scope);
 }
 for(const line of lines){for(let i=0;i<line.units.length;i++)for(let j=i+1;j<line.units.length;j++)compare(line.units[i],line.units[j],'inner');}
 // End-to-word: next three lines within a section, plus first line across a section break.
 for(let i=0;i<lines.length;i++){const line=lines[i],last=line.units.at(-1);for(let j=i+1;j<Math.min(lines.length,i+4);j++){if(lines[j].section!==line.section&&j!==i+1)break;for(const unit of lines[j].units)compare(last,unit,lines[j].section===line.section?'outer':'section',false);}}
 // End groups span the entire song, including distant sections.
 const endingGroups=new Map(),schemeKeys=new Map();
 for(const line of lines){const last=line.units.at(-1),key=last.sound?.key;if(!key)continue;if(!schemeKeys.has(key))schemeKeys.set(key,schemeKeys.size);const ix=schemeKeys.get(key);line.scheme=String.fromCharCode(65+ix%26)+(ix>=26?Math.floor(ix/26):'');if(!endingGroups.has(key))endingGroups.set(key,[]);const previous=endingGroups.get(key);for(const prev of previous)compare(prev,last,'end',false);previous.push(last);}
 const multiGroups=new Map();for(const line of lines)for(const size of [2,3]){const tail=line.units.slice(-size);if(tail.length<size||tail.some(u=>!u.sound))continue;const key=tail.map(u=>u.sound.key).join('/');for(const prev of multiGroups.get(key)||[]){if(prev.map(u=>u.text).join('')!==tail.map(u=>u.text).join(''))add('multi',prev.at(-1),tail.at(-1),'end',{aIds:prev.map(u=>u.id),bIds:tail.map(u=>u.id),size});}if(!multiGroups.has(key))multiGroups.set(key,[]);multiGroups.get(key).push(tail);}
 const repeatedLines=new Map();for(const line of lines){const key=line.words.join('|');if(!key)continue;const prev=repeatedLines.get(key);if(prev){add('phrase',prev.units[0],line.units[0],'song',{aIds:prev.units.map(u=>u.id),bIds:line.units.map(u=>u.id)});}else repeatedLines.set(key,line);}
 const counts=Object.fromEntries(Object.keys(names).map(type=>[type,edges.filter(e=>e.type===type).length]));
 for(const [type,n] of Object.entries(counts))features.push('density:'+type+':'+bucket(n/Math.max(1,units.length)));
 features.push('length:'+Math.min(12,Math.floor(units.length/50)),'sections:'+Math.min(10,section+1),'linecount:'+Math.min(15,Math.floor(lines.length/4)));
 const structures=[];for(let s=0;s<=section;s++){const local=lines.filter(l=>l.section===s),map=new Map();const scheme=local.map(l=>{if(l.scheme==='?')return '?';if(!map.has(l.scheme))map.set(l.scheme,String.fromCharCode(65+map.size));return map.get(l.scheme);}).join('');structures.push({section:s,scheme,from:local[0]?.number,to:local.at(-1)?.number});for(let i=0;i+3<local.length;i+=4){const keys=local.slice(i,i+4).map(l=>l.scheme),seen=new Map();const shape=keys.map(k=>{if(k==='?')return '?';if(!seen.has(k))seen.set(k,String.fromCharCode(65+seen.size));return seen.get(k);}).join('');features.push('scheme:'+shape);}}
 return {text,tokens,lines:lines.length,lineDetails:lines,units,edges,features,counts,structures,sections,recognized:units.filter(u=>u.sound).length};
}
const CUTS_LOG=[4,5,Math.log10(500000),6,Math.log10(5000000),7];
function erf(x){const s=x>=0?1:-1;x=Math.abs(x);const t=1/(1+0.3275911*x);const y=1-(((((1.061405429*t-1.453152027)*t)+1.421413741)*t-0.284496736)*t+0.254829592)*t*Math.exp(-x*x);return s*y;}
const normCdf=(x,mu,sig)=>0.5*(1+erf((x-mu)/(sig*Math.SQRT2)));
const q4=v=>Math.round(v*10000)/10000;
function extractDoc(text,a){
 const rawText=text||a.text||'';
 const wordsMap=new Map(),bigrams=new Map(),cgrams=new Map(),rhymes=new Map(),struct=new Map();
 let engWords=0,numWords=0,thaiWords=0,longWords=0,shortWords=0;const uniqueEng=new Set();
 for(let i=0;i<a.tokens.length;i++){
  const w=a.tokens[i];wordsMap.set(w,(wordsMap.get(w)||0)+1);
  if(/^[a-z]+$/i.test(w)){engWords++;uniqueEng.add(w);}else if(/^\d+$/.test(w))numWords++;else if(/[ก-๛]/.test(w))thaiWords++;
  if(w.length>=6)longWords++;if(w.length<=2)shortWords++;
  if(i+1<a.tokens.length){const bg=w+'|'+a.tokens[i+1];bigrams.set(bg,(bigrams.get(bg)||0)+1);}
  if(w.length>=3&&w.length<=12){for(let k=0;k<=w.length-3;k++){const g=w.slice(k,k+3);cgrams.set(g,(cgrams.get(g)||0)+1);}}
 }
 const rawLines=rawText.split(/\r?\n/).map(l=>l.trim()).filter(l=>l&&!/^\[.*\]$/.test(l));
 const lineFreq=new Map();let maxLineFreq=0,dupLines=0,sumLen=0,sumLen2=0;
 for(const l of rawLines){const norm=l.toLowerCase().replace(/\s+/g,' ');const c=(lineFreq.get(norm)||0)+1;lineFreq.set(norm,c);if(c>maxLineFreq)maxLineFreq=c;if(c>1)dupLines++;sumLen+=l.length;sumLen2+=l.length*l.length;}
 const nLines=Math.max(1,rawLines.length||a.lines||1),avgLen=sumLen/nLines,stdLen=Math.sqrt(Math.max(0,sumLen2/nLines-avgLen*avgLen));
 const chars=Math.max(1,rawText.length),blankLines=(rawText.match(/\r?\n\s*\r?\n/g)||[]).length;
 for(const f of a.features){if(f.startsWith('r:vowel:')||f.startsWith('r:multi:'))rhymes.set(f,(rhymes.get(f)||0)+1);else if(!f.startsWith('w:')&&!f.startsWith('r:'))struct.set(f,(struct.get(f)||0)+1);}
 const nWords=Math.max(1,a.tokens.length),nUnits=Math.max(1,a.units?a.units.length:(a.unitsCount||1)),nUnique=wordsMap.size,nSections=Math.max(1,(a.structures||[]).length);
 const counts=a.counts||{vowel:0,onset:0,coda:0,assonance:0,near:0,repeat:0,multi:0,phrase:0};
 const dense=[
  Math.log1p(nWords),Math.log1p(nUnits),Math.log1p(nLines),Math.log1p(nUnique),
  nUnique/nWords,dupLines/nLines,Math.log1p(maxLineFreq),lineFreq.size/nLines,
  nWords/nLines,nUnits/nWords,nLines/nSections,Math.log1p(nSections),Math.log1p(blankLines),
  engWords/nWords,Math.log1p(uniqueEng.size),thaiWords/nWords,numWords/nWords,
  longWords/nWords,shortWords/nWords,(a.recognized||0)/nUnits,
  Math.log1p(avgLen),Math.log1p(stdLen),stdLen/Math.max(1,avgLen),Math.log1p(chars),
  /\[[^\]]+\]/.test(rawText)?1:0,(rawText.match(/[()]/g)||[]).length/nLines,(rawText.match(/[!?]/g)||[]).length/nLines,
  (rawText.match(/่/g)||[]).length/chars,(rawText.match(/้/g)||[]).length/chars,(rawText.match(/๊/g)||[]).length/chars,(rawText.match(/๋/g)||[]).length/chars,
  counts.vowel/nUnits,counts.onset/nUnits,counts.coda/nUnits,counts.assonance/nUnits,counts.near/nUnits,counts.repeat/nUnits,
  counts.multi/nLines,counts.phrase/nLines,(counts.vowel+counts.multi)/nLines
 ];
 return {words:wordsMap,bigrams,cgrams,rhymes,struct,dense};
}
function train(rows,includePairs=true,numClasses=7){
 const hasViews=rows.length>=50&&rows.every(r=>Number.isFinite(+r.views)&&+r.views>0)&&numClasses===7;
 if(!hasViews){
  const counts=Array.from({length:numClasses},()=>({})),totals=Array(numClasses).fill(0),docs=Array(numClasses).fill(0),vocab=new Set();
  for(const r of rows){docs[r.label]++;const features=r.features||analyze(r.lyrics).features;for(const f of features){if(!includePairs&&f.startsWith('r:'))continue;vocab.add(f);counts[r.label][f]=(counts[r.label][f]||0)+1;totals[r.label]++;}}
  return {type:'nb',counts,totals,docs,vocab:[...vocab],n:rows.length,version:3};
 }
 const N=rows.length,docs=Array(numClasses).fill(0),extracted=[],rhymeFreq=new Map();
 for(const r of rows){
  docs[r.label]++;
  const a=r.analysis||analyze(r.lyrics);
  if(includePairs)for(const f of a.features)if(f.startsWith('r:'))rhymeFreq.set(f,(rhymeFreq.get(f)||0)+1);
  extracted.push(extractDoc(r.lyrics,a));
 }
 const df=new Map();
 const addM=(m,p,seen)=>{for(const k of m.keys()){const fk=p+k;if(!seen.has(fk)){seen.add(fk);df.set(fk,(df.get(fk)||0)+1);}}};
 for(const f of extracted){
  const seen=new Set();
  addM(f.words,'w:',seen);
  if(includePairs){addM(f.bigrams,'b:',seen);addM(f.cgrams,'c:',seen);addM(f.rhymes,'r:',seen);}
  addM(f.struct,'s:',seen);
 }
 const vocab=[],vocabMap=new Map(),idf=[];
 const maxD=Math.floor(N*0.95);
 for(const [k,d] of df.entries()){
  const p=k.slice(0,2);
  const minD=p==='w:'?2:p==='b:'?5:p==='c:'?8:p==='r:'?8:2;
  if(d<minD||d>maxD)continue;
  vocabMap.set(k,vocab.length);vocab.push(k);idf.push(Math.log((N+1)/(d+1))+1);
 }
 const V=vocab.length,D=extracted[0].dense.length;
 const mean=new Float64Array(D),std=new Float64Array(D);
 for(const f of extracted)for(let d=0;d<D;d++)mean[d]+=f.dense[d];
 for(let d=0;d<D;d++)mean[d]/=N;
 for(const f of extracted)for(let d=0;d<D;d++){const diff=f.dense[d]-mean[d];std[d]+=diff*diff;}
 for(let d=0;d<D;d++)std[d]=Math.sqrt(std[d]/N)||1;
 const weights={w:1,b:0.8,c:0.6,r:0.4,s:0.5},denseScale=0.30;
 const X=extracted.map(f=>{
  const vec=[];let norm2=0;
  const pushM=(m,p,w)=>{for(const [k,cnt] of m.entries()){const vid=vocabMap.get(p+k);if(vid===undefined)continue;const v=(1+Math.log(cnt))*idf[vid]*w;vec.push([vid,v]);norm2+=v*v;}};
  pushM(f.words,'w:',weights.w);
  if(includePairs){pushM(f.bigrams,'b:',weights.b);pushM(f.cgrams,'c:',weights.c);pushM(f.rhymes,'r:',weights.r);}
  pushM(f.struct,'s:',weights.s);
  const norm=Math.sqrt(norm2)||1;for(const pair of vec)pair[1]/=norm;
  const dvec=new Float64Array(D);for(let d=0;d<D;d++)dvec[d]=Math.max(-4,Math.min(4,(f.dense[d]-mean[d])/std[d]))*denseScale;
  return {vec,dvec};
 });
 // 1. Complement Naive Bayes on L2-normalized TF-IDF
 const alpha=0.5,classSum=Array.from({length:numClasses},()=>new Float64Array(V)),totalSum=new Float64Array(V),classTotals=new Float64Array(numClasses);
 for(let i=0;i<N;i++){const c=rows[i].label;for(const [vid,v] of X[i].vec){classSum[c][vid]+=v;totalSum[vid]+=v;classTotals[c]+=v;}}
 const grandTotal=classTotals.reduce((a,b)=>a+b,0);
 const priors=docs.map(n=>(n+1)/(N+numClasses));
 const cnbW=Array.from({length:numClasses},()=>new Array(V)),cnbB=new Array(numClasses);
 for(let c=0;c<numClasses;c++){
  cnbB[c]=q4(0.6*Math.log(priors[c]));
  const denom=(grandTotal-classTotals[c])+alpha*V;
  for(let j=0;j<V;j++)cnbW[c][j]=q4(-Math.log(((totalSum[j]-classSum[c][j])+alpha)/denom));
 }
 if(!includePairs){
  return {type:'cnb-v3',vocab,idf:idf.map(q4),cnbW,cnbB,tempCnb:0.35,priors:priors.map(q4),weights,docs,n:N,version:3};
 }
 // 2. Ordinal Ridge Regression on log10(views) -> Gaussian CDF band probabilities
 const totalDim=V+D,yLog=rows.map(r=>Math.log10(Math.max(100,+r.views))),yMean=yLog.reduce((a,b)=>a+b,0)/N;
 const W=new Float64Array(totalDim),vW=new Float64Array(totalDim),gW=new Float64Array(totalDim);
 let b=yMean,vb=0;const invN=1/N,l2=0.002;
 for(let ep=0;ep<140;ep++){
  gW.fill(0);let gb=0;
  for(let i=0;i<N;i++){
   const {vec,dvec}=X[i];let pred=b;
   for(let k=0;k<vec.length;k++)pred+=W[vec[k][0]]*vec[k][1];
   for(let d=0;d<D;d++)pred+=W[V+d]*dvec[d];
   const err=pred-yLog[i];gb+=err;
   for(let k=0;k<vec.length;k++)gW[vec[k][0]]+=err*vec[k][1];
   for(let d=0;d<D;d++)gW[V+d]+=err*dvec[d];
  }
  vb=0.88*vb-0.5*(gb*invN);b+=vb;
  for(let j=0;j<totalDim;j++){vW[j]=0.88*vW[j]-0.5*(gW[j]*invN+l2*W[j]);W[j]+=vW[j];}
 }
 let mse=0;
 for(let i=0;i<N;i++){
  const {vec,dvec}=X[i];let pred=b;
  for(let k=0;k<vec.length;k++)pred+=W[vec[k][0]]*vec[k][1];
  for(let d=0;d<D;d++)pred+=W[V+d]*dvec[d];
  mse+=(pred-yLog[i])**2;
 }
 const sig=Math.sqrt(mse/N)*1.25;
 const rhymePairs=[...rhymeFreq.entries()].filter(([,n])=>n>=3).sort((a,b)=>b[1]-a[1]).slice(0,25000);
 return {
  type:'hybrid-v3',version:3,n:N,docs,priors:priors.map(q4),
  vocab,idf:idf.map(q4),weights,denseScale,
  mean:Array.from(mean,q4),std:Array.from(std,q4),
  ridgeW:Array.from(W,q4),ridgeB:q4(b),ridgeSig:q4(sig),
  cnbW,cnbB,tempCnb:0.35,blendRidge:0.70,tau:0.20,
  rhymePairs
 };
}
const vocabCache=new WeakMap();
function predict(model,text,precomputed){
 const analysis=precomputed||analyze(text);
 if(model.type==='nb'||model.version===2){
  if(!vocabCache.has(model))vocabCache.set(model,new Set(model.vocab));
  const known=vocabCache.get(model);
  const scores=model.docs.map((n,c)=>Math.log((n+1)/(model.n+model.docs.length)));
  for(const f of analysis.features)if(known.has(f))for(let c=0;c<scores.length;c++)scores[c]+=Math.log(((model.counts[c][f]||0)+1)/(model.totals[c]+known.size));
  const max=Math.max(...scores),exp=scores.map(s=>Math.exp(s-max)),sum=exp.reduce((a,b)=>a+b,0);
  return {analysis,prob:exp.map(v=>v/sum),label:scores.indexOf(max),knownWords:analysis.tokens.filter(w=>known.has('w:'+w)).length};
 }
 if(!vocabCache.has(model)){const m=new Map();for(let i=0;i<model.vocab.length;i++)m.set(model.vocab[i],i);vocabCache.set(model,m);}
 const vmap=vocabCache.get(model),doc=extractDoc(text||analysis.text||'',analysis);
 const vec=[];let norm2=0;
 const pushM=(m,p,w)=>{for(const [k,cnt] of m.entries()){const vid=vmap.get(p+k);if(vid===undefined)continue;const v=(1+Math.log(cnt))*model.idf[vid]*w;vec.push([vid,v]);norm2+=v*v;}};
 pushM(doc.words,'w:',model.weights.w);
 if(model.type==='hybrid-v3'){pushM(doc.bigrams,'b:',model.weights.b);pushM(doc.cgrams,'c:',model.weights.c);pushM(doc.rhymes,'r:',model.weights.r);}
 pushM(doc.struct,'s:',model.weights.s);
 const norm=Math.sqrt(norm2)||1;for(const pair of vec)pair[1]/=norm;
 const K=model.docs.length;
 const scCnb=new Array(K);let mxCnb=-Infinity;
 for(let c=0;c<K;c++){let s=model.cnbB[c],wc=model.cnbW[c];for(let k=0;k<vec.length;k++)s+=wc[vec[k][0]]*vec[k][1];scCnb[c]=s*model.tempCnb;if(scCnb[c]>mxCnb)mxCnb=scCnb[c];}
 const eCnb=scCnb.map(s=>Math.exp(s-mxCnb)),sumCnb=eCnb.reduce((a,b)=>a+b,0),pCnb=eCnb.map(v=>v/sumCnb);
 let prob=pCnb;
 if(model.type==='hybrid-v3'){
  const V=model.vocab.length,D=model.mean.length;
  let pred=model.ridgeB;
  for(let k=0;k<vec.length;k++)pred+=model.ridgeW[vec[k][0]]*vec[k][1];
  for(let d=0;d<D;d++){const z=Math.max(-4,Math.min(4,(doc.dense[d]-model.mean[d])/model.std[d]))*model.denseScale;pred+=model.ridgeW[V+d]*z;}
  const pCdf=new Array(K);let prev=0;
  for(let c=0;c<6;c++){const cur=normCdf(CUTS_LOG[c],pred,model.ridgeSig);pCdf[c]=Math.max(1e-6,cur-prev);prev=cur;}
  pCdf[6]=Math.max(1e-6,1-prev);
  const sCdf=pCdf.reduce((a,x)=>a+x,0);
  const wR=model.blendRidge;
  const raw=pCdf.map((v,c)=>wR*(v/sCdf)+(1-wR)*pCnb[c]);
  const adj=raw.map((p,c)=>Math.log(Math.max(1e-12,p))-model.tau*Math.log(model.priors[c]));
  const mxA=Math.max(...adj),eA=adj.map(s=>Math.exp(s-mxA)),sA=eA.reduce((a,b)=>a+b,0);
  prob=eA.map(v=>v/sA);
 }
 let best=0;for(let c=1;c<K;c++)if(prob[c]>prob[best])best=c;
 return {analysis,prob,label:best,knownWords:analysis.tokens.filter(w=>vmap.has('w:'+w)).length};
}
if(root.NAVIBAY_SYLLABLES)setDictionary(root.NAVIBAY_SYLLABLES);
root.NaviBay={words,sound,syllables,setDictionary,analyze,train,predict,names,pairKey,rhyme:w=>sound(w)?.key||null};
})(typeof module==='object'?module.exports:globalThis);
