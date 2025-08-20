from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from io import BytesIO
import requests
import pymupdf as fitz
import ast
from datetime import datetime
import os
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

app = FastAPI()

# Enable CORS for frontend access
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "*"
    ],  # يمكنك تقييدها لاحقًا إلى ["https://mohamedmohy0.github.io"]
    allow_credentials=True,  # Change to frontend URL in production
    allow_methods=["*"],
    allow_headers=["*"],
)

# === Supabase Info ===
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Iml2cmZobGpsbXpuY2lrY2J3aHlyIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc1MzU2NjM5MSwiZXhwIjoyMDY5MTQyMzkxfQ.JsIusJF4oQxPFUdPiIceYOWdKpBfDKrOTxRquq2VzG4"
SUPABASE_HEADERS = {
    "apikey": SUPABASE_KEY,
    "Authorization": f"Bearer {SUPABASE_KEY}"
}

# URLs for tables
QUESTION_URL = "https://ivrfhljlmzncikcbwhyr.supabase.co/rest/v1/MR.Ahmad"
USERS_URL = "https://ivrfhljlmzncikcbwhyr.supabase.co/rest/v1/MR.Belal.users"
QUIZ_URL = "https://ivrfhljlmzncikcbwhyr.supabase.co/rest/v1/MR.Belal.quiz"
Test_URL = "https://ivrfhljlmzncikcbwhyr.supabase.co/rest/v1/MR.Belal.test"
# === GET PAGE ENDPOINT ===


@app.get("/")
def read_root():
    return {"message": "FastAPI is working ✅"}


@app.get("/get_page")
def get_pdf_page(email: str, grade: str, lecture_number: int,
                 question_number: int):
    # === Step 1: Validate user SolveState ===
    user_params = {"email": f"eq.{email}", "select": "SolveState"}
    user_response = requests.get(USERS_URL,
                                 headers=SUPABASE_HEADERS,
                                 params=user_params)

    if user_response.status_code != 200:
        raise HTTPException(status_code=500,
                            detail="Error accessing users table")

    user_data = user_response.json()
    if not user_data:
        raise HTTPException(status_code=404, detail="User not found")

    user_state = user_data[0]["SolveState"]
    if user_state < lecture_number:
        raise HTTPException(status_code=403,
                            detail="❌ غير مسموح بعرض هذه المحاضرة حالياً")

    # === Step 2: Choose correct PDF file based on grade and lecture ===
    if grade == "الأول الثانوي":
        BASE_DIR = os.path.dirname(os.path.abspath(__file__))
        pdf_path = os.path.join(BASE_DIR, "Data1_1.pdf")
        with open(pdf_path, "rb") as f:
            pdf_bytes = f.read()
            doc = fitz.open(stream=pdf_bytes, filetype="pdf")
            print("عدد الصفحات:", doc.page_count)
    elif grade == "الثاني الثانوي":
        pdf_path = f"Data2_{lecture_number}.pdf"
    elif grade == "الثالث الثانوي":
        pdf_path = f"Data3_{lecture_number}.pdf"
    else:
        raise HTTPException(status_code=400, detail="الصف الدراسي غير صحيح")

    # === Step 3: Map question_number to page number directly ===
    page_number = question_number - 1  # Zero-based index

    # === Step 4: Render and return the PDF page ===
    try:
        doc = fitz.open(pdf_path)
        if page_number < 0 or page_number >= len(doc):
            raise HTTPException(status_code=404,
                                detail="رقم الصفحة خارج النطاق")

        page = doc.load_page(page_number)
        pix = page.get_pixmap()
        img_bytes = BytesIO(pix.tobytes("jpeg"))

        return StreamingResponse(img_bytes, media_type="image/jpeg")

    except Exception as e:
        print(f"🔥 Error rendering PDF page: {e}")
        raise HTTPException(status_code=500, detail=f"Internal Error: {e}")


# === LOGIN ENDPOINT ===


@app.post("/login")
async def login_user(req: Request):
    body = await req.json()
    email = body.get("email")
    password = body.get("password")

    if not email or not password:
        raise HTTPException(status_code=400,
                            detail="Missing email or password")

    params = {"email": f"eq.{email}", "select": "*"}
    response = requests.get(USERS_URL, headers=SUPABASE_HEADERS, params=params)

    if response.status_code != 200:
        raise HTTPException(status_code=500,
                            detail="Error accessing users table")

    users = response.json()
    if not users:
        raise HTTPException(status_code=401, detail="User not found")

    user = users[0]
    if user["password"] != password:
        raise HTTPException(status_code=401, detail="Wrong password")

    name = user.get("Name", "").strip()
    needs_info = name == ""

    return {
        "level": user["Level"],
        "name": name,
        "message": "Login successful",
        "needs_info": needs_info
    }


@app.post("/update_user_info")
async def update_user_info(req: Request):
    try:
        body = await req.json()
        email = body.get("email")
        name = body.get("name", "").strip()
        phone = body.get("phone", "").strip()
        center = body.get("center", "").strip()
        level = body.get("level", "").strip()
    except Exception:
        raise HTTPException(status_code=400,
                            detail="⚠️ تنسيق البيانات غير صالح")

    if not email or not name or not phone or not center or not level:
        raise HTTPException(status_code=400,
                            detail="❌ الرجاء إدخال جميع البيانات المطلوبة")

    update_data = {
        "Level": level,
        "Name": name,
        "Phone": phone,
        "Location": center
    }

    response = requests.patch(f"{USERS_URL}?email=eq.{email}",
                              headers={
                                  **SUPABASE_HEADERS, "Content-Type":
                                  "application/json"
                              },
                              json=update_data)

    print("Response status code:", response.status_code)
    print("Response content:", response.text)

    if response.status_code in (200, 204):
        return {"message": "✅ تم حفظ البيانات بنجاح"}
    else:
        detail = response.text
        raise HTTPException(status_code=500,
                            detail=f"⚠️ فشل في تحديث البيانات: {detail}")


@app.get("/get_quiz_info")
def get_quiz_info(email: str, quiz_number: int):
    # جلب بيانات المستخدم

    user_params = {
        "email": f"eq.{email}",
        "select": "QuizState,QuizScore,QuizDate,Name,Level"
    }
    response = requests.get(USERS_URL,
                            headers=SUPABASE_HEADERS,
                            params=user_params)

    if response.status_code != 200:
        raise HTTPException(status_code=500,
                            detail="Error accessing users table")

    user_data = response.json()
    if not user_data:
        raise HTTPException(status_code=404, detail="User not found")

    user = user_data[0]
    level = user["Level"]
    quiz_state = user.get("QuizState")
    print(f"📊 quiz_number المطلوب: {quiz_number}")
    print(f"🔐 QuizState من قاعدة البيانات: {quiz_state}")
    if int(quiz_number) > int(quiz_state):
        raise HTTPException(status_code=404,
                            detail="غير مسموح بحل هذا الواجب بعد")

    # قراءة بيانات score/date وتحويلها إلى list إذا كانت string
    try:
        scores_raw = user.get("QuizScore", "[]") or "[]"
        dates_raw = user.get("QuizDate", "[]") or "[]"

        try:
            scores = ast.literal_eval(scores_raw) if isinstance(
                scores_raw, str) else scores_raw
        except:
            scores = []

        try:
            dates = ast.literal_eval(dates_raw) if isinstance(
                dates_raw, str) else dates_raw
        except:
            dates = []

        if isinstance(scores, str):
            scores = ast.literal_eval(scores)
        if isinstance(dates, str):
            dates = ast.literal_eval(dates)

        if not isinstance(scores, list):
            scores = []
        if not isinstance(dates, list):
            dates = []

    except Exception as e:
        print("⚠️ Error parsing Score or Date:", e)
        scores = []
        dates = []

    # تحميل بيانات الواجب لمعرفة عدد الصفحات
    if level == "الأول الثانوي":
        pdf_path = f"Quiz1_{quiz_number}.pdf"
    elif level == "الثاني الثانوي":
        pdf_path = f"Quiz2_{quiz_number}.pdf"
    elif level == "الثالث الثانوي":
        pdf_path = f"Quiz3_{quiz_number}.pdf"
    else:
        raise HTTPException(status_code=400, detail="الصف الدراسي غير معروف")
    try:
        print(f"📂 محاولة فتح الملف: {pdf_path}")
        doc = fitz.open(pdf_path)
        page_count = len(doc)
        print(f"📄 عدد الصفحات: {page_count}")
    except Exception as e:
        print(f"❌ فشل فتح ملف PDF: {e}")
        raise HTTPException(status_code=500,
                            detail="غير مسموح بحل هذا الواجب بعد")

    # تحقق هل تم الحل مسبقًا
    index = quiz_number - 1
    if len(scores) > index and scores[index] is not None:
        score = scores[index]
        date = dates[index] if len(dates) > index else "غير معروف"

        try:
            score_val = float(score)
        except (ValueError, TypeError):
            score_val = 0

        # حساب النسبة بناءً على عدد صفحات PDF
        percentage = round((score_val / page_count) * 100)

        return {
            "already_done": True,
            "quiz_number": quiz_number,
            "score": score_val,
            "percentage": percentage,
            "date": date,
            "name": user.get("Name", "بدون اسم"),
            "page_count": len(doc)
        }

    # جلب الأجوبة الصحيحة
    # جلب الأجوبة الصحيحة
    answers_params = {
        "QuizNum": f"eq.{quiz_number}",
        "Level":
        f"eq.{level}",  # تأكد أن `level` تم تعريفه مسبقًا (من بيانات المستخدم)
        "select": "Answer"
    }
    answers_res = requests.get(QUIZ_URL,
                               headers=SUPABASE_HEADERS,
                               params=answers_params)

    print(f"🔁 status code: {answers_res.status_code}")
    print(f"📦 raw data: {answers_res.text}")

    if answers_res.status_code != 200:
        raise HTTPException(status_code=500, detail="Error fetching answers")

    answer_data = answers_res.json()
    if not answer_data:
        raise HTTPException(status_code=404, detail="Answers not found")

    print(f"✅ answer_data = {answer_data}")

    correct_answers = ast.literal_eval(answer_data[0]["Answer"])

    return {
        "already_done": False,
        "quiz_number": quiz_number,
        "page_count": page_count,
        "answers": correct_answers,
        "name": user.get("Name", "بدون اسم")
    }


# === [2] Serve individual quiz page as image ===
@app.get("/get_quiz_page")
def get_quiz_page(email: str, page: int, quiz_number: int):
    global level
    # Step 1: Get user level and quiz state
    user_params = {"email": f"eq.{email}", "select": "Level,QuizState"}
    user_response = requests.get(USERS_URL,
                                 headers=SUPABASE_HEADERS,
                                 params=user_params)

    if user_response.status_code != 200 or not user_response.json():
        raise HTTPException(status_code=404, detail="User not found")

    user = user_response.json()[0]
    level = user["Level"]
    quiz_state = user["QuizState"]

    # Step 2: Determine file path based on level
    if level == "الأول الثانوي":
        pdf_path = f"Quiz1_{quiz_number}.pdf"
    elif level == "الثاني الثانوي":
        pdf_path = f"Quiz2_{quiz_number}.pdf"
    elif level == "الثالث الثانوي":
        pdf_path = f"Quiz3_{quiz_number}.pdf"
    else:
        raise HTTPException(status_code=400, detail="الصف الدراسي غير معروف")

    # Step 3: Open PDF and return requested page
    try:
        doc = fitz.open(pdf_path)
        if page < 0 or page >= len(doc):
            raise HTTPException(status_code=404, detail="رقم الصفحة غير صحيح")

        pix = doc.load_page(page).get_pixmap()
        img_bytes = BytesIO(pix.tobytes("jpeg"))
        return StreamingResponse(img_bytes, media_type="image/jpeg")
    except Exception as e:
        raise HTTPException(status_code=500,
                            detail=f"Error rendering page: {e}")


@app.post("/submit_score")
async def submit_score(req: Request):
    try:
        data = await req.json()
        email = data.get("email")
        quiz_number_raw = data.get("quiz_number")

        if email is None or quiz_number_raw is None:
            raise HTTPException(status_code=400,
                                detail="email and quiz_number are required")

        quiz_number = int(quiz_number_raw)

        # جلب كل محاولات هذا المستخدم لهذا الواجب من جدول quiz_attempts
        attempts_params = {
            "email": f"eq.{email}",
            "quiz_number": f"eq.{quiz_number}",
            "select": "status"
        }
        attempts_res = requests.get(
            "https://ivrfhljlmzncikcbwhyr.supabase.co/rest/v1/MR.Belal.quiz_attempts",
            headers=SUPABASE_HEADERS,
            params=attempts_params)
        if attempts_res.status_code != 200:
            raise HTTPException(status_code=500,
                                detail="Failed to fetch quiz attempts")

        attempts_data = attempts_res.json()
        # حساب عدد الأسئلة الصحيحة
        correct_count = sum(1 for attempt in attempts_data
                            if attempt["status"] == "correct")

        # جلب بيانات المستخدم
        user_params = {
            "email": f"eq.{email}",
            "select": "QuizState, QuizScore, QuizDate"
        }
        user_response = requests.get(USERS_URL,
                                     headers=SUPABASE_HEADERS,
                                     params=user_params)
        if user_response.status_code != 200:
            raise HTTPException(status_code=500,
                                detail="Error accessing users table")

        user_json = user_response.json()
        if not user_json:
            raise HTTPException(status_code=404, detail="User not found")

        user_data = user_json[0]

        quiz_state = user_data.get("QuizState")
        if quiz_state is None:
            raise HTTPException(status_code=400,
                                detail="User QuizState not set")

        if quiz_number > quiz_state:
            raise HTTPException(status_code=403,
                                detail="Cannot submit score for locked quiz")

        import json

        raw_score = user_data.get("QuizScore") or []
        raw_date = user_data.get("QuizDate") or []

        try:
            score_list = json.loads(raw_score) if isinstance(
                raw_score, str) else raw_score
        except json.JSONDecodeError:
            score_list = []

        try:
            date_list = json.loads(raw_date) if isinstance(raw_date,
                                                           str) else raw_date
        except json.JSONDecodeError:
            date_list = []

        index = quiz_number - 1

        while len(score_list) <= index:
            score_list.append(None)
        while len(date_list) <= index:
            date_list.append(None)

        # تحديث الدرجة الفعلية بناءً على حساب عدد الأسئلة الصحيحة من الجدول quiz_attempts
        score_list[index] = correct_count
        date_list[index] = datetime.now().strftime("%Y-%m-%d")

        update_data = {"QuizScore": score_list, "QuizDate": date_list}

        patch_response = requests.patch(f"{USERS_URL}?email=eq.{email}",
                                        headers={
                                            **SUPABASE_HEADERS, "Content-Type":
                                            "application/json",
                                            "Prefer": "return=representation"
                                        },
                                        json=update_data)

        if patch_response.status_code not in (200, 204):
            print("Patch response error:", patch_response.text)
            raise HTTPException(status_code=500,
                                detail="Failed to update score history")

        return {
            "message": "✅ Score and date saved successfully",
            "score": correct_count,
            "date": date_list[index]
        }

    except Exception as e:
        import traceback
        print("🔥 Exception in submit_score:", str(e))
        traceback.print_exc()
        raise HTTPException(status_code=500,
                            detail=f"Internal Server Error: {e}")


@app.get("/can_solve_quiz")
def can_solve_quiz(email: str, requested_quiz: int):
    params = {"email": f"eq.{email}", "select": "QuizState"}
    response = requests.get(USERS_URL, headers=SUPABASE_HEADERS, params=params)

    if response.status_code != 200:
        raise HTTPException(status_code=500, detail="Error checking QuizState")

    user_data = response.json()
    if not user_data:
        raise HTTPException(status_code=404, detail="User not found")

    current_state = user_data[0]["QuizState"]

    if requested_quiz > current_state:
        raise HTTPException(status_code=403,
                            detail="❌ لا يمكنك حل هذا الواجب الآن")

    return {"message": "✅ يمكنك حل هذا الاختبار"}


@app.get("/get_quiz_page_count")
def get_quiz_page_count(quiz_number: int, quiz_S):
    try:
        file_path = "Quiz{quiz_number}.pdf"
        doc = fitz.open(file_path)
        return {"page_count": len(doc)}
    except:
        raise HTTPException(status_code=403,
                            detail="❌ لا يمكنك حل هذا الواجب الآن")


@app.post("/submit_attempt")
async def submit_answer_attempt(req: Request):
    data = await req.json()
    email = data.get("email")
    quiz_number = int(data.get("quiz_number"))
    question_index = int(data.get("question_index"))
    selected_option = data.get("selected_option")
    if not all([
            email, quiz_number is not None, question_index is not None,
            selected_option
    ]):
        raise HTTPException(status_code=400, detail="Missing required fields")

    user_params = {"email": f"eq.{email}", "select": "Level,QuizState"}
    user_response = requests.get(USERS_URL,
                                 headers=SUPABASE_HEADERS,
                                 params=user_params)

    if user_response.status_code != 200 or not user_response.json():
        raise HTTPException(status_code=404, detail="User not found")

    user = user_response.json()[0]
    level = user["Level"]
    answer_params = {
        "QuizNum": f"eq.{quiz_number}",
        "Level":
        f"eq.{level}",  # تأكد أن `level` تم تعريفه مسبقًا (من بيانات المستخدم)
        "select": "Answer"
    }
    answer_res = requests.get(QUIZ_URL,
                              headers=SUPABASE_HEADERS,
                              params=answer_params)
    if answer_res.status_code != 200 or not answer_res.json():
        raise HTTPException(status_code=404, detail="Answers not found")

    answer_list = ast.literal_eval(answer_res.json()[0]["Answer"])
    if question_index >= len(answer_list):
        raise HTTPException(status_code=400, detail="Invalid question index")

    correct_answer = str(answer_list[question_index]).strip()
    selected_option = selected_option.strip()
    is_correct = selected_option == correct_answer

    # التحقق من محاولة سابقة
    query_params = {
        "email": f"eq.{email}",
        "quiz_number": f"eq.{quiz_number}",
        "question_index": f"eq.{question_index}"
    }
    res = requests.get(
        "https://ivrfhljlmzncikcbwhyr.supabase.co/rest/v1/MR.Belal.quiz_attempts",
        headers=SUPABASE_HEADERS,
        params={
            **query_params, "select": "*"
        })

    existing = res.json()
    locked = False
    attempts = 0
    status = ""

    if existing:
        record = existing[0]
        attempts = record["attempts"]
        if record["locked"]:
            return {
                "locked": True,
                "status": record["status"],
                "attempts": attempts
            }

        if is_correct:
            locked = True
            status = "correct"
        elif attempts == 0:
            status = "wrong-once"
            attempts = 1
        else:
            status = "wrong"
            locked = True
            attempts = 2

        update_data = {
            "selected_option": selected_option,
            "attempts": attempts,
            "status": status,
            "locked": locked,
            "last_updated": datetime.now().isoformat()
        }

        patch = requests.patch(
            f"https://ivrfhljlmzncikcbwhyr.supabase.co/rest/v1/MR.Belal.quiz_attempts?email=eq.{email}&quiz_number=eq.{quiz_number}&question_index=eq.{question_index}",
            headers={
                **SUPABASE_HEADERS, "Content-Type": "application/json"
            },
            json=update_data)
    else:
        if is_correct:
            locked = True
            status = "correct"
        else:
            status = "wrong-once"
            attempts = 1

        insert_data = {
            "email": email,
            "quiz_number": quiz_number,
            "question_index": question_index,
            "selected_option": selected_option,
            "correct_answer": correct_answer,
            "attempts": attempts,
            "status": status,
            "locked": locked,
            "last_updated": datetime.now().isoformat()
        }

        post = requests.post(
            "https://ivrfhljlmzncikcbwhyr.supabase.co/rest/v1/MR.Belal.quiz_attempts",
            headers={
                **SUPABASE_HEADERS, "Content-Type": "application/json"
            },
            json=insert_data)

    return {"locked": locked, "status": status, "attempts": attempts}


@app.get("/get_attempts")
def get_attempts(email: str, quiz_number: int):
    params = {
        "email": f"eq.{email}",
        "quiz_number": f"eq.{quiz_number}",
        "select": "question_index,status,locked"
    }
    res = requests.get(
        "https://ivrfhljlmzncikcbwhyr.supabase.co/rest/v1/MR.Belal.quiz_attempts",
        headers=SUPABASE_HEADERS,
        params=params)

    if res.status_code != 200:
        raise HTTPException(status_code=500, detail="Failed to load attempts")

    attempts = res.json()
    return {
        entry["question_index"]: {
            "status": entry["status"],
            "locked": entry["locked"]
        }
        for entry in attempts
    }


@app.get("/get_test_page_count")
def get_test_page_count(test_number: int):
    try:
        file_path = "Test{test_number}.pdf"
        doc = fitz.open(file_path)
        return {"page_count": len(doc)}
    except:
        raise HTTPException(status_code=403,
                            detail="❌ لا يمكنك حل هذا الواجب الآن")


from datetime import datetime, timedelta, timezone

import logging

logging.basicConfig(level=logging.INFO)  # إعداد logging


@app.get("/get_test_info")
def get_test_info(email: str, test_number: int):
    try:
        # ===== 1) جلب بيانات المستخدم =====
        user_params = {
            "email": f"eq.{email}",
            "select": "TestState,TestScore,TestDate,Name,Level,EndHour"
        }
        response = requests.get(USERS_URL,
                                headers=SUPABASE_HEADERS,
                                params=user_params)
        logging.info(f"GET {USERS_URL} returned status {response.status_code}")
        user_data = response.json()
        logging.info(f"user_data: {user_data}")
        if not user_data:
            raise HTTPException(status_code=404, detail="المستخدم غير مسجل")
        user = user_data[0]
        level = user.get("Level")
        test_state = user.get("TestState")
        end_hour = user.get("EndHour")
        logging.info(
            f"User: {user}, level: {level}, test_state: {test_state}, end_hour: {end_hour}"
        )

        # ===== 2) معالجة النتائج السابقة =====
        scores, dates = [], []
        try:
            scores = ast.literal_eval(user.get("TestScore", "[]"))
            dates = ast.literal_eval(user.get("TestDate", "[]"))
        except Exception as e:
            logging.warning(f"فشل تحويل TestScore أو TestDate إلى قائمة: {e}")
        logging.info(f"scores: {scores}, dates: {dates}")

        index = test_number - 1

        # ===== 3) جلب بيانات الاختبار =====
        test_res = requests.get(Test_URL,
                                headers=SUPABASE_HEADERS,
                                params={
                                    "TestNum": f"eq.{test_number}",
                                    "Level": f"eq.{level}",
                                    "select":
                                    "Answer,Time,Show_Solve,AllowedDate"
                                })
        logging.info(f"GET {Test_URL} returned status {test_res.status_code}")
        test_info = test_res.json()
        logging.info(f"test_info: {test_info}")
        if not test_info:
            raise HTTPException(status_code=404,
                                detail="لا توجد بيانات لهذا الاختبار")
        test = test_info[0]

        show_solve = test.get("Show_Solve", False)
        allowed_date = test.get("AllowedDate")
        duration_hours = test.get("Time", 1)
        logging.info(
            f"Test: show_solve={show_solve}, allowed_date={allowed_date}, duration_hours={duration_hours}"
        )

        now = datetime.now(timezone.utc)

        # ===== 4) إذا كان الاختبار من النوع الذي يعرض الحلول مباشرة =====
        if show_solve:
            if len(scores) > index and scores[index] is not None:
                pdf_path = {
                    "الأول الثانوي": f"Test1_{test_number}.pdf",
                    "الثاني الثانوي": f"Test2_{test_number}.pdf",
                    "الثالث الثانوي": f"Test3_{test_number}.pdf"
                }.get(level, "")
                page_count = 1
                if pdf_path:
                    try:
                        with fitz.open(pdf_path) as doc:
                            page_count = len(doc)
                    except Exception as e:
                        logging.warning(f"تعذر فتح ملف PDF: {e}")
                score = float(scores[index])
                date = dates[index] if index < len(dates) else "غير معروف"
                return {
                    "status":
                    "completed",
                    "test_number":
                    test_number,
                    "score":
                    score,
                    "total_questions":
                    page_count,
                    "date":
                    date,
                    "name":
                    user.get("Name", "طالب"),
                    "show_solve":
                    True,
                    "answers":
                    test.get("Answer", "").split(",") if isinstance(
                        test.get("Answer", ""), str) else test.get(
                            "Answer", [])
                }
            else:
                return {
                    "status": "not_completed",
                    "message": "لم تقم بحل هذا الاختبار بعد",
                    "show_solve": True
                }

        # ===== 5) إذا كان الاختبار لا يعرض الحلول مباشرة (التدفق العادي) =====

        # تحقق من allowed_date
        if allowed_date:
            day_end = datetime.strptime(allowed_date, "%Y-%m-%d")
            logging.info(f"Allowed date: {day_end}")
            if now.date() > day_end.date():
                logging.info("Test expired based on allowed_date")
                return {
                    "status": "finished_day_over",
                    "message": "انتهى وقت الاختبار، إجاباتك قد تم إرسالها"
                }

        # تحقق من وجود نتيجة سابقة
        if len(scores) > index and scores[index] is not None:
            return {
                "status": "completed_no_show",
                "message": "تم إرسال إجاباتك، انتظر النتيجة"
            }

        # تحقق من صلاحية الاختبار
        if test_number > test_state:
            raise HTTPException(status_code=403,
                                detail="⚠️ لم يفتح هذا الاختبار بعد")

        # التحقق من end_hour
        if end_hour:
            end_dt = datetime.fromisoformat(end_hour)
            if now > end_dt:
                return {
                    "status": "time_over",
                    "message": "انتهت مدة الاختبار",
                    "score": scores[index] if index < len(scores) else None,
                    "show_solve": False
                }
        else:
            # أول مرة يبدأ فيها المستخدم الاختبار
            end_dt = now + timedelta(hours=duration_hours)
            logging.info(f"Setting new end_hour: {end_dt}")

            # تحديث Supabase لحفظ EndHour
            patch_res = requests.patch(USERS_URL,
                                       headers=SUPABASE_HEADERS,
                                       json={"EndHour": end_dt.isoformat()},
                                       params={"email": f"eq.{email}"})
            logging.info(
                f"PATCH response: {patch_res.status_code}, {patch_res.text}")
            if patch_res.status_code not in [200, 204]:
                logging.warning(f"فشل حفظ EndHour للمستخدم {email}")

        # تحضير بيانات الاختبار الجديد
        pdf_path = {
            "الأول الثانوي": f"Test1_{test_number}.pdf",
            "الثاني الثانوي": f"Test2_{test_number}.pdf",
            "الثالث الثانوي": f"Test3_{test_number}.pdf"
        }.get(level)
        if not pdf_path:
            raise HTTPException(status_code=400,
                                detail="الصف الدراسي غير مدعوم")
        try:
            with fitz.open(pdf_path) as doc:
                page_count = len(doc)
        except Exception as e:
            raise HTTPException(status_code=500,
                                detail=f"تعذر تحميل ملف الاختبار: {e}")

        try:
            correct_answers = ast.literal_eval(test.get("Answer", "[]"))
        except:
            correct_answers = test.get("Answer", "").split(",")
        if isinstance(correct_answers, list):
            correct_answers = [ans.strip() for ans in correct_answers]

        logging.info(
            f"Prepared test data: page_count={page_count}, correct_answers={correct_answers}"
        )

        return {
            "status": "new",
            "test_number": test_number,
            "page_count": page_count,
            "duration_hours": duration_hours,
            "answers": correct_answers,
            "name": user.get("Name", "طالب"),
            "level": level,
            "end_hour": end_dt.isoformat(),
            "show_solve": False
        }

    except HTTPException as he:
        raise he
    except Exception as e:
        logging.exception("خطأ غير متوقع")
        raise HTTPException(status_code=500, detail=f"خطأ غير متوقع: {str(e)}")


@app.get("/get_test_page")
def get_test_page(email: str, page: int, test_number: int):
    global level
    # Step 1: Get user level and quiz state
    user_params = {"email": f"eq.{email}", "select": "Level,TestState"}
    user_response = requests.get(USERS_URL,
                                 headers=SUPABASE_HEADERS,
                                 params=user_params)

    if user_response.status_code != 200 or not user_response.json():
        raise HTTPException(status_code=404, detail="User not found")

    user = user_response.json()[0]
    level = user["Level"]
    test_state = user["TestState"]

    # Step 2: Determine file path based on level
    if level == "الأول الثانوي":
        pdf_path = f"Test1_{test_number}.pdf"
    elif level == "الثاني الثانوي":
        pdf_path = f"Test2_{test_number}.pdf"
    elif level == "الثالث الثانوي":
        pdf_path = f"Test3_{test_number}.pdf"
    else:
        raise HTTPException(status_code=400, detail="الصف الدراسي غير معروف")

    # Step 3: Open PDF and return requested page
    try:
        doc = fitz.open(pdf_path)
        if page < 0 or page >= len(doc):
            raise HTTPException(status_code=404, detail="رقم الصفحة غير صحيح")

        pix = doc.load_page(page).get_pixmap()
        img_bytes = BytesIO(pix.tobytes("jpeg"))
        return StreamingResponse(img_bytes, media_type="image/jpeg")
    except Exception as e:
        raise HTTPException(status_code=500,
                            detail=f"Error rendering page: {e}")


@app.get("/can_solve_test")
def can_solve_test(email: str, requested_test: int):
    params = {"email": f"eq.{email}", "select": "TestState"}
    response = requests.get(USERS_URL, headers=SUPABASE_HEADERS, params=params)

    if response.status_code != 200:
        raise HTTPException(status_code=500, detail="Error checking TestState")

    user_data = response.json()
    if not user_data:
        raise HTTPException(status_code=404, detail="User not found")

    current_state = user_data[0]["TestState"]

    if requested_test > current_state:
        raise HTTPException(status_code=403,
                            detail="❌ لا يمكنك حل هذا الواجب الآن")

    return {"message": "✅ يمكنك حل هذا الاختبار"}


# @app.post("/submit_test_score")
# async def submit_test_score(req: Request):
#     try:
#         data = await req.json()
#         email = data.get("email")
#         test_number_raw = data.get("test_number")
#         answers = data.get("answers", {})  # {question_index: selected_option}

#         if not email or not test_number_raw:
#             raise HTTPException(status_code=400,
#                                 detail="email and test_number are required")

#         test_number = int(test_number_raw)

#         # جلب بيانات المستخدم
#         user_params = {
#             "email": f"eq.{email}",
#             "select": "TestState,TestScore,TestDate,Level"
#         }
#         user_response = requests.get(USERS_URL,
#                                      headers=SUPABASE_HEADERS,
#                                      params=user_params)
#         if user_response.status_code != 200:
#             raise HTTPException(status_code=500,
#                                 detail="Error accessing users table")

#         user_json = user_response.json()
#         if not user_json:
#             raise HTTPException(status_code=404, detail="User not found")

#         user_data = user_json[0]
#         level = user_data.get("Level")
#         test_state = user_data.get("TestState")

#         # قراءة الدرجات والتواريخ السابقة
#         raw_score = user_data.get("TestScore") or []
#         raw_date = user_data.get("TestDate") or []

#         try:
#             score_list = ast.literal_eval(raw_score) if isinstance(
#                 raw_score, str) else raw_score
#         except:
#             score_list = []

#         try:
#             date_list = ast.literal_eval(raw_date) if isinstance(
#                 raw_date, str) else raw_date
#         except:
#             date_list = []

#         index = test_number - 1

#         if len(score_list) > index and score_list[index] is not None:
#             raise HTTPException(
#                 status_code=403,
#                 detail="❌ لقد أكملت هذا الاختبار مسبقًا ولا يمكنك إعادة إرساله"
#             )

#         # جلب الإجابات الصحيحة من جدول الاختبارات
#         answers_params = {
#             "TestNum": f"eq.{test_number}",
#             "Level": f"eq.{level}",
#             "select": "Answer"
#         }
#         answers_res = requests.get(Test_URL,
#                                    headers=SUPABASE_HEADERS,
#                                    params=answers_params)
#         if answers_res.status_code != 200:
#             raise HTTPException(status_code=500,
#                                 detail="Error fetching correct answers")

#         correct_answers_data = answers_res.json()
#         if not correct_answers_data:
#             raise HTTPException(status_code=404,
#                                 detail="Correct answers not found")

#         raw_correct = correct_answers_data[0].get("Answer", "[]")
#         try:
#             parsed = ast.literal_eval(raw_correct) if isinstance(
#                 raw_correct, str) else raw_correct
#             correct_answers = [str(ans).strip() for ans in parsed]
#         except (ValueError, SyntaxError):
#             correct_answers = [
#                 str(ans).strip() for ans in raw_correct.split(",")
#             ]

#         print("✅ الإجابات الصحيحة:", correct_answers)
#         print("📩 إجابات المستخدم:", answers)

#         # حساب النقاط
#         correct_count = 0
#         for q_index, user_answer in answers.items():
#             q_index = int(q_index)
#             if q_index < len(correct_answers) and str(
#                     user_answer).strip() == correct_answers[q_index]:
#                 correct_count += 1

#         print(f"🎯 النتيجة النهائية: {correct_count}")

#         # تحديث السجلات
#         while len(score_list) <= index:
#             score_list.append(None)
#         while len(date_list) <= index:
#             date_list.append(None)

#         score_list[index] = correct_count
#         date_list[index] = datetime.now().strftime("%Y-%m-%d")

#         update_data = {"TestScore": score_list, "TestDate": date_list}

#         if test_number == test_state:
#             update_data["TestState"] = test_state + 1

#         patch_response = requests.patch(f"{USERS_URL}?email=eq.{email}",
#                                         headers={
#                                             **SUPABASE_HEADERS, "Content-Type":
#                                             "application/json",
#                                             "Prefer": "return=representation"
#                                         },
#                                         json=update_data)

#         if patch_response.status_code not in (200, 204):
#             print("Patch response error:", patch_response.text)
#             raise HTTPException(status_code=500,
#                                 detail="Failed to update test results")

#         return {
#             "message": "✅ تم حفظ النتيجة بنجاح",
#             "score": correct_count,
#             "date": date_list[index],
#             "test_state_updated": test_number == test_state
#         }

#     except Exception as e:
#         import traceback
#         traceback.print_exc()
#         raise HTTPException(status_code=500,
#                             detail=f"Internal Server Error: {str(e)}")


@app.post("/submit_test_score")
async def submit_test_score(req: Request):
    try:
        data = await req.json()
        email = data.get("email")
        test_number_raw = data.get("test_number")

        if not email or not test_number_raw:
            raise HTTPException(status_code=400,
                                detail="email and test_number are required")

        test_number = int(test_number_raw)

        # جلب بيانات المستخدم
        user_params = {
            "email": f"eq.{email}",
            "select": "TestState,TestScore,TestDate,Level"
        }
        user_response = requests.get(USERS_URL,
                                     headers=SUPABASE_HEADERS,
                                     params=user_params)
        if user_response.status_code != 200:
            raise HTTPException(status_code=500,
                                detail="Error accessing users table")

        user_json = user_response.json()
        if not user_json:
            raise HTTPException(status_code=404, detail="User not found")

        user_data = user_json[0]
        test_state = user_data.get("TestState")

        # قراءة الدرجات والتواريخ السابقة
        raw_score = user_data.get("TestScore") or []
        raw_date = user_data.get("TestDate") or []

        try:
            score_list = ast.literal_eval(raw_score) if isinstance(
                raw_score, str) else raw_score
        except:
            score_list = []

        try:
            date_list = ast.literal_eval(raw_date) if isinstance(
                raw_date, str) else raw_date
        except:
            date_list = []

        index = test_number - 1

        if len(score_list) > index and score_list[index] is not None:
            raise HTTPException(
                status_code=403,
                detail="❌ لقد أكملت هذا الاختبار مسبقًا ولا يمكنك إعادة إرساله"
            )

        # حساب الدرجة من المحاولات المحفوظة
        correct_count = calculate_test_score(email, test_number)

        # تحديث السجلات
        while len(score_list) <= index:
            score_list.append(None)
        while len(date_list) <= index:
            date_list.append(None)

        score_list[index] = correct_count
        date_list[index] = datetime.now().strftime("%Y-%m-%d")

        update_data = {"TestScore": score_list, "TestDate": date_list}

        if test_number == test_state:
            update_data["TestState"] = test_state + 1

        patch_response = requests.patch(f"{USERS_URL}?email=eq.{email}",
                                        headers={
                                            **SUPABASE_HEADERS, "Content-Type":
                                            "application/json",
                                            "Prefer": "return=representation"
                                        },
                                        json=update_data)

        if patch_response.status_code not in (200, 204):
            print("Patch response error:", patch_response.text)
            raise HTTPException(status_code=500,
                                detail="Failed to update test results")

        return {
            "message": "✅ تم حفظ النتيجة بنجاح",
            "score": correct_count,
            "date": date_list[index],
            "test_state_updated": test_number == test_state
        }

    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500,
                            detail=f"Internal Server Error: {str(e)}")


@app.post("/submit_test_on_timeout")
async def submit_test_on_timeout(req: Request):
    try:
        print(f"Incoming request: {await req.body()}")

        data = await req.json()
        print(f"Parsed data: {data}")

        email = data.get("email")
        test_number_raw = data.get("test_number")

        if not email:
            raise HTTPException(status_code=400, detail="Email is required")
        if not test_number_raw:
            raise HTTPException(status_code=400,
                                detail="Test number is required")

        data = await req.json()
        email = data.get("email")
        test_number_raw = data.get("test_number")

        if not email or not test_number_raw:
            raise HTTPException(status_code=400,
                                detail="email and test_number are required")

        test_number = int(test_number_raw)

        # جلب بيانات المستخدم
        user_params = {
            "email": f"eq.{email}",
            "select": "TestState,TestScore,TestDate,Level"
        }
        user_response = requests.get(USERS_URL,
                                     headers=SUPABASE_HEADERS,
                                     params=user_params)
        if user_response.status_code != 200:
            raise HTTPException(status_code=500,
                                detail="Error accessing users table")

        user_json = user_response.json()
        if not user_json:
            raise HTTPException(status_code=404, detail="User not found")

        user_data = user_json[0]
        test_state = user_data.get("TestState")

        # قراءة الدرجات والتواريخ السابقة
        raw_score = user_data.get("TestScore") or []
        raw_date = user_data.get("TestDate") or []

        try:
            score_list = ast.literal_eval(raw_score) if isinstance(
                raw_score, str) else raw_score
        except:
            score_list = []

        try:
            date_list = ast.literal_eval(raw_date) if isinstance(
                raw_date, str) else raw_date
        except:
            date_list = []

        index = test_number - 1

        if len(score_list) > index and score_list[index] is not None:
            return {
                "message": "تم إرسال هذا الاختبار مسبقاً",
                "score": score_list[index],
                "date": date_list[index] if len(date_list) > index else None
            }

        # حساب الدرجة من المحاولات المحفوظة
        correct_count = calculate_test_score(email, test_number)

        # تحديث السجلات
        while len(score_list) <= index:
            score_list.append(None)
        while len(date_list) <= index:
            date_list.append(None)

        score_list[index] = correct_count
        date_list[index] = datetime.now().strftime("%Y-%m-%d")

        update_data = {"TestScore": score_list, "TestDate": date_list}

        if test_number == test_state:
            update_data["TestState"] = test_state + 1

        patch_response = requests.patch(f"{USERS_URL}?email=eq.{email}",
                                        headers={
                                            **SUPABASE_HEADERS, "Content-Type":
                                            "application/json",
                                            "Prefer": "return=representation"
                                        },
                                        json=update_data)

        if patch_response.status_code not in (200, 204):
            print("Patch response error:", patch_response.text)
            raise HTTPException(status_code=500,
                                detail="Failed to update test results")

        return {
            "message": "✅ تم حفظ النتيجة تلقائياً بعد انتهاء الوقت",
            "score": correct_count,
            "date": date_list[index],
            "test_state_updated": test_number == test_state
        }

    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500,
                            detail=f"Internal Server Error: {str(e)}")


@app.post("/save_test_attempt")
async def save_test_attempt(req: Request):
    try:
        data = await req.json()
        print("📥 Received data:", data)

        email = data.get("email")
        test_number = data.get("test_number")
        question_index = data.get("question_index")
        selected_option = data.get("selected_option")

        # تحقق من البيانات المرسلة
        if not all([
                email, test_number is not None, question_index is not None,
                selected_option
        ]):
            print("❌ Missing required fields")
            raise HTTPException(status_code=400,
                                detail="Missing required fields")

        # جلب الإجابات الصحيحة من جدول الأسئلة
        answer_params = {"TestNum": f"eq.{test_number}", "select": "Answer"}
        print("🔍 Fetching answers with params:", answer_params)
        answer_res = requests.get(Test_URL,
                                  headers=SUPABASE_HEADERS,
                                  params=answer_params)
        print("📡 Supabase response status:", answer_res.status_code)
        print("📡 Supabase response body:", answer_res.text)

        if answer_res.status_code != 200 or not answer_res.json():
            raise HTTPException(status_code=404, detail="Answers not found")

        try:
            answer_list = ast.literal_eval(answer_res.json()[0]["Answer"])
        except Exception as e:
            print("❌ Failed to parse answers:", str(e))
            raise HTTPException(status_code=500,
                                detail="Invalid answers format in DB")

        if question_index >= len(answer_list):
            print(
                f"❌ Invalid question index: {question_index} / total questions: {len(answer_list)}"
            )
            raise HTTPException(status_code=400,
                                detail="Invalid question index")

        correct_answer = str(answer_list[question_index]).strip()
        print("✅ Correct answer for this question:", correct_answer)

        # تجهيز بيانات الحفظ
        attempt_data = {
            "email": email,
            "test_number": test_number,
            "question_index": question_index,
            "selected_option": selected_option.strip(),
            "correct_answer": correct_answer,
            "updated_at": datetime.utcnow().isoformat()
        }
        print("💾 Attempt data to save:", attempt_data)

        # حفظ أو تحديث المحاولة
        upsert_res = requests.post(
            "https://ivrfhljlmzncikcbwhyr.supabase.co/rest/v1/MR.Belal.test_attempts",
            headers={
                **SUPABASE_HEADERS, "Content-Type": "application/json",
                "Prefer": "resolution=merge-duplicates"
            },
            params={"on_conflict":
                    "email,test_number,question_index"},  # <== هذا هو المفتاح
            json=[attempt_data])
        print("📡 Supabase upsert status:", upsert_res.status_code)
        print("📡 Supabase upsert body:", upsert_res.text)

        if upsert_res.status_code not in (200, 201):
            raise HTTPException(
                status_code=500,
                detail=f"Failed to save attempt: {upsert_res.text}")

        return {"status": "saved"}

    except Exception as e:
        print("🔥 Unexpected error:", str(e))
        raise


def calculate_test_score(email, test_number):
    """Calculate score from saved attempts"""
    # جلب كل محاولات هذا المستخدم لهذا الاختبار
    attempts_params = {
        "email": f"eq.{email}",
        "test_number": f"eq.{test_number}",
        "select": "question_index,selected_option"
    }
    attempts_res = requests.get(
        "https://ivrfhljlmzncikcbwhyr.supabase.co/rest/v1/MR.Belal.test_attempts",
        headers=SUPABASE_HEADERS,
        params=attempts_params)

    if attempts_res.status_code != 200:
        raise HTTPException(status_code=500,
                            detail="Failed to fetch test attempts")

    attempts_data = attempts_res.json()

    # جلب الإجابات الصحيحة
    user_params = {"email": f"eq.{email}", "select": "Level"}
    user_res = requests.get(USERS_URL,
                            headers=SUPABASE_HEADERS,
                            params=user_params)
    if user_res.status_code != 200:
        raise HTTPException(status_code=500,
                            detail="Error fetching user level")

    user_level = user_res.json()[0]["Level"]

    answers_params = {
        "TestNum": f"eq.{test_number}",
        "Level": f"eq.{user_level}",
        "select": "Answer"
    }
    answers_res = requests.get(Test_URL,
                               headers=SUPABASE_HEADERS,
                               params=answers_params)

    if answers_res.status_code != 200:
        raise HTTPException(status_code=500,
                            detail="Error fetching correct answers")

    correct_answers_data = answers_res.json()
    if not correct_answers_data:
        raise HTTPException(status_code=404,
                            detail="Correct answers not found")

    # تحليل الإجابات الصحيحة
    raw_correct = correct_answers_data[0].get("Answer", "[]")
    try:
        correct_answers = ast.literal_eval(raw_correct) if isinstance(
            raw_correct, str) else raw_correct
    except (ValueError, SyntaxError):
        correct_answers = [ans.strip() for ans in raw_correct.split(",")]

    # حساب النقاط
    correct_count = 0
    for attempt in attempts_data:
        q_index = attempt["question_index"]
        user_answer = str(attempt["selected_option"]).strip()
        if q_index < len(correct_answers) and user_answer == str(
                correct_answers[q_index]).strip():
            correct_count += 1

    return correct_count


import traceback


def clean_answer(ans):
    """
    تنظيف الإجابة بحيث تعود كـ string مفردة.
    يتعامل مع list أو string بصيغة ['ج'] أو "[ج]"
    """
    if not ans:
        return ''
    if isinstance(ans, list):
        return str(ans[0]) if ans else ''
    if isinstance(ans, str):
        ans = ans.strip()
        if ans.startswith('[') and ans.endswith(']'):
            try:
                parsed = ast.literal_eval(ans)
                return str(parsed[0]) if parsed else ''
            except:
                return ans
    return str(ans)


@app.get("/get_saved_answers")
def get_saved_answers(email: str, test_number: int):
    try:
        params = {
            "email": f"eq.{email}",
            "test_number": f"eq.{test_number}",
            "select": "question_index,selected_option,correct_answer",
            "order": "question_index.asc"
        }

        response = requests.get(
            "https://ivrfhljlmzncikcbwhyr.supabase.co/rest/v1/MR.Belal.test_attempts",
            headers=SUPABASE_HEADERS,
            params=params)

        if response.status_code != 200:
            raise Exception(f"Error fetching data: {response.text}")

        data = response.json()
        print("\n--- البيانات المسترجعة من Supabase ---")
        print(data)

        if not data:
            print("⚠️ لا توجد بيانات لهذا الاختبار")
            return {"message": "لا توجد بيانات لهذا الاختبار"}

        saved_answers = {}
        correct_answers = {}

        for item in data:
            q_index = str(item['question_index'])  # تحويل المفتاح إلى string

            selected = clean_answer(item.get('selected_option', ''))
            correct = clean_answer(item.get('correct_answer', ''))

            saved_answers[q_index] = selected
            correct_answers[q_index] = correct

            print(
                f"سؤال {q_index}: الإجابة المختارة = {selected} | الإجابة الصحيحة = {correct}"
            )

        return {
            "saved_answers": saved_answers,
            "correct_answers": correct_answers
        }

    except Exception as e:
        raise HTTPException(status_code=500,
                            detail=f"Error retrieving answers: {str(e)}")



