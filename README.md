# MLProject

โปรเจกต์ Machine Learning ของทีม Nowl-Solutions

## โปรเจกต์ในรีโปนี้

| โฟลเดอร์ | คำอธิบาย |
|---|---|
| [`navibay/`](navibay/README.md) | **NaviBay** วิเคราะห์สัมผัสในเนื้อเพลงไทยทั้งเพลง และทายช่วงยอดวิว 7 ช่วงด้วย Naive Bayes ร่วมกับ Ridge ฝึกด้วย Python (scikit-learn, PyThaiNLP) และมีหน้าเว็บที่ประมวลผลบนเบราว์เซอร์ |

## เริ่มต้นใช้งาน NaviBay

```bash
cd navibay
pip install -r requirements.txt
python test.py                    # รันชุดทดสอบ
python train.py data/songs.csv    # ฝึกโมเดลใหม่และ export ไปที่ dist/model.js
python server.py                  # เปิด http://127.0.0.1:4173
```

ต้องใช้ Python 3.11 ขึ้นไป รายละเอียดวิธีวิเคราะห์ ผลการวัด และข้อจำกัดดูได้ที่ [navibay/README.md](navibay/README.md)

## CI

GitHub Actions รัน `navibay/test.py` อัตโนมัติทุกครั้งที่มี push ไป `main` และทุก pull request ที่แก้ไฟล์ใน `navibay/`
