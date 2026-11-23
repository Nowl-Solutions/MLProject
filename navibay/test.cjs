const assert=require('node:assert/strict'),fs=require('node:fs');const {NaviBay:N}=require('./dist/engine.js');N.setDictionary(fs.readFileSync('dist/vendor/syllables-th.txt','utf8').split(/\r?\n/));require('./dist/model.js');
assert.equal(N.rhyme('ใจ'),N.rhyme('ไกล'));assert.equal(N.rhyme('รัก'),N.rhyme('พัก'));assert.equal(N.rhyme('คิด'),N.rhyme('จิต'));assert.equal(N.rhyme('เธอ'),N.rhyme('เจอ'));assert.equal(N.rhyme('รอ'),N.rhyme('ขอ'));assert.notEqual(N.rhyme('ใจ'),N.rhyme('กาย'));
assert.equal(N.sound('ฟ้า').onset,N.sound('ฝัน').onset);assert.notEqual(N.sound('กล้า').onset,N.sound('กา').onset);
assert.deepEqual(N.syllables('หัวใจ').map(s=>s.text),['หัว','ใจ']);assert.deepEqual(N.syllables('ความหวัง').map(s=>s.text),['ความ','หวัง']);
// Loanwords
assert.equal(N.rhyme('สไตล์'),N.rhyme('ใจ'));assert.equal(N.rhyme('เบียร์'),N.rhyme('เชียร์'));assert.equal(N.rhyme('แคร์'),N.rhyme('แพ้'));assert.equal(N.rhyme('ป๊อป'),N.rhyme('สต็อป'));assert.equal(N.rhyme('ดรอป'),N.rhyme('ชอบ'));assert.equal(N.rhyme('เทรนด์'),N.rhyme('เป็น'));assert.equal(N.rhyme('แทร็ป'),N.rhyme('แร็ป'));assert.equal(N.rhyme('ฟีล'),N.rhyme('ปีน'));assert.equal(N.rhyme('กรูฟ'),N.rhyme('จูบ'));
// Complex อักษรนำ, false clusters, ร หัน, multi-letter karan
assert.deepEqual(N.syllables('สบาย').map(s=>s.text),['ส','บาย']);assert(N.analyze('สบาย\nกาย').edges.some(e=>e.type==='vowel'&&e.scope==='outer'));
assert.deepEqual(N.syllables('อร่อย').map(s=>s.text),['อ','ร่อย']);assert(N.analyze('อร่อย\nคอย').edges.some(e=>e.type==='vowel'&&e.scope==='outer'));
assert.deepEqual(N.syllables('ถนน').map(s=>s.text),['ถ','นน']);assert(N.analyze('ถนน\nคน').edges.some(e=>e.type==='vowel'&&e.scope==='outer'));
assert.deepEqual(N.syllables('สวรรค์').map(s=>s.text),['ส','วรรค์']);assert(N.analyze('สวรรค์\nฝัน').edges.some(e=>e.type==='vowel'&&e.scope==='outer'));
assert.equal(N.rhyme('จันทร์'),N.rhyme('ฝัน'));assert.equal(N.rhyme('ศาสตร์'),N.rhyme('ขาด'));assert.equal(N.rhyme('ธรรม'),N.rhyme('คำ'));
assert.equal(N.rhyme('สร้าง'),N.rhyme('ทาง'));assert.equal(N.sound('สร้าง').onset,'s');assert.equal(N.rhyme('เศร้า'),N.rhyme('เหงา'));assert.equal(N.sound('เศร้า').onset,'s');assert.equal(N.rhyme('ทรง'),N.rhyme('หลง'));assert.equal(N.sound('ทรง').onset,'s');
// Regional dialects (Isan, Northern, Southern)
assert.equal(N.rhyme('บ่'),N.rhyme('ก็'));assert.equal(N.rhyme('ฮู้'),N.rhyme('รู้'));assert.equal(N.rhyme('ฮัก'),N.rhyme('รัก'));assert.equal(N.rhyme('เด้อ'),N.rhyme('เธอ'));assert.equal(N.rhyme('ซ่อย'),N.rhyme('คอย'));assert.equal(N.rhyme('คึด'),N.rhyme('ยึด'));assert.equal(N.rhyme('แซ่บ'),N.rhyme('แอบ'));
assert.equal(N.rhyme('เปิ้น'),N.rhyme('เดิน'));assert.equal(N.rhyme('ปิ๊ก'),N.rhyme('พริก'));assert.equal(N.rhyme('กิ๋น'),N.rhyme('ดิน'));assert.equal(N.rhyme('ใจ๋'),N.rhyme('ไกล'));assert.equal(N.rhyme('แต๊'),N.rhyme('แท้'));
assert.equal(N.rhyme('หรอย'),N.rhyme('คอย'));assert.equal(N.rhyme('หม้าย'),N.rhyme('กาย'));assert.equal(N.rhyme('หนัด'),N.rhyme('ชัด'));assert.equal(N.rhyme('พรือ'),N.rhyme('มือ'));
const a=N.analyze('[Verse]\nใจ ไป ไกล\nรัก พัก\n\n[Chorus]\nรัก พัก\nใจ ไป ไกล');assert.equal(a.lines,4);assert.equal(a.structures.length,2);assert.equal(a.lineDetails[0].number,2);assert(a.counts.phrase>0);assert(a.edges.some(e=>e.type==='vowel'&&e.scope==='inner'));assert(a.edges.some(e=>e.type==='repeat'&&e.scope!=='inner'));assert(!a.tokens.includes('Verse'));
for(const u of a.units)assert.equal(a.lineDetails[u.line].raw.slice(u.start,u.end),u.text);
const cross=N.analyze('ใจ\nไกล');assert(cross.edges.some(e=>e.type==='vowel'&&e.scope==='outer'));
assert(N.analyze('ใจ กาย').edges.some(e=>e.type==='near'));assert(!N.analyze('ใจ กาย').edges.some(e=>e.type==='vowel'));
assert(N.analyze('รัก ฝัน').edges.some(e=>e.type==='assonance'));assert(N.analyze('รัก มาก').edges.some(e=>e.type==='coda'));
assert(N.analyze('ฟ้า ฝัน').edges.some(e=>e.type==='onset'));
assert(N.analyze('ใจ ใจ').edges.every(e=>e.type==='repeat'));
assert(N.analyze('ขอ ใจ\nรอ ไกล').edges.some(e=>e.type==='multi'&&e.size===2));
assert.equal(N.analyze('ใจ\nไกล\nรัก\nพัก').structures[0].scheme,'AABB');assert.equal(N.analyze('ใจ\nรัก\nไกล\nพัก').structures[0].scheme,'ABAB');
assert.equal(N.analyze('english only').recognized,0);assert.equal(N.analyze('').units.length,0);
const model=N.train([{lyrics:'รัก รัก ใจ',label:0},{lyrics:'ดาว ฟ้า ฝัน',label:1},{lyrics:'ทะเล ลม คลื่น',label:2}],true,3);assert.equal(N.predict(model,'รัก รัก').label,0);
const full=Array.from({length:40},(_,i)=>i%2?'รอ ใจ ไกล':'รัก พัก ฝัน').join('\n');const r=N.predict(globalThis.NAVIBAY_MODEL,full);assert.equal(r.analysis.lines,40);assert.equal(r.prob.length,7);assert(r.prob.every(Number.isFinite));assert(Math.abs(r.prob.reduce((a,b)=>a+b,0)-1)<1e-9);assert(r.knownWords>0);
const m=globalThis.NAVIBAY_MODEL.meta;assert.equal(m.train+m.test,m.usable);assert.equal(m.matrix.flat().reduce((a,b)=>a+b,0),m.test);assert.equal(m.classCounts.length,7);assert.equal(m.perClass.reduce((s,c)=>s+c.test,0),m.test);assert.deepEqual(m.cuts,[10000,100000,500000,1000000,5000000,10000000]);
console.log('PASS: syllables, vowel lengths, consonants, all 8 relation types, source positions, stanza boundaries, AABB/ABAB, full-song inference, 7 classes and evaluation counts');
