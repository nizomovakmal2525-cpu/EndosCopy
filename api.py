import os
import uuid
import json
from fastapi import APIRouter, UploadFile, File, Form, HTTPException, Security, Depends
from fastapi.security.api_key import APIKeyHeader
from fastapi.responses import JSONResponse
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.messages import SystemMessage, HumanMessage
import database


def run_image_search(file_path: str):
    from trained_model.search import search
    return search(file_path)

router = APIRouter(prefix="/api/v1")

api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)

async def get_api_user(api_key: str = Security(api_key_header)):
    if not api_key:
        raise HTTPException(
            status_code=403,
            detail="X-API-Key headeri topilmadi."
        )
    
    user = database.get_user_by_api_key(api_key)
    if user:
        return user
    
    raise HTTPException(
        status_code=403,
        detail="Noto'g'ri API Token."
    )

llm = ChatGoogleGenerativeAI(
    model="gemini-2.5-flash",
    temperature=0.1,
    api_key=os.getenv("GOOGLE_API_KEY"),  # .env faylidan olinadi
    response_mime_type="application/json"
)

@router.post("/predict")
async def api_predict(
    file: UploadFile = File(...),
    age: str = Form(...),
    gender: str = Form(...),
    api_user = Depends(get_api_user)
):
    try:
        age_int = int(age)
    except ValueError:
        raise HTTPException(status_code=422, detail="Bemor yoshi butun son bo'lishi kerak")

    # Rasmni saqlash
    image_bytes = await file.read()
    file_ext = file.filename.split(".")[-1]
    file_name = f"{uuid.uuid4()}.{file_ext}"
    file_path = os.path.join(database.UPLOADS_DIR, file_name)
    
    with open(file_path, "wb") as f:
        f.write(image_bytes)

    try:
        # 1. CLIP model orqali qidirish
        search_result = run_image_search(file_path)
        
        if "error" in search_result:
            return JSONResponse(status_code=500, content={"error": search_result["error"]})

        disease = search_result["disease"]
        confidence = int(search_result["confidence"])

        # 2. Gemini orqali tahlil
        prompt = f"""
        Bemor haqida ma'lumot:
        - Yoshi: {age_int}
        - Jinsi: {gender}
        
        Endoskopik tahlil natijasi (CLIP model orqali):
        - Aniqlangan holat: {disease}
        - Aniqlik darajasi: {confidence}%
        
        Siz tajribali gastroenterologsiz. Ushbu ma'lumotlarga asoslanib, bemor uchun o'zbek tilida:
        1. Qisqa va lo'nda klinik tavsif (description) yozing.
        2. Kamida 3-4 ta foydali tavsiya (recommendation) bering.
        
        Javobni FAQAT JSON formatida qaytaring:
        {{
            "description": "...",
            "recommendation": ["...", "...", ...]
        }}
        """

        messages = [
            SystemMessage(content="Siz tibbiy tahlillarni sharhlovchi professional shifokorsiz. Javobni faqat o'zbek tilida va JSON formatida qaytaring."),
            HumanMessage(content=prompt),
        ]
        
        response = await llm.agenerate([messages])
        gemini_result_text = response.generations[0][0].text.strip()
        
        # JSONni tozalash
        if "```json" in gemini_result_text:
            gemini_result_text = gemini_result_text.split("```json")[1].split("```")[0].strip()
        elif "```" in gemini_result_text:
            gemini_result_text = gemini_result_text.split("```")[1].strip()
            
        gemini_json = json.loads(gemini_result_text)

        result_json = {
            "disease": disease,
            "confidence": confidence,
            "description": gemini_json.get("description", ""),
            "recommendation": gemini_json.get("recommendation", []),
            "image_url": f"/uploads/{file_name}"
        }

        # Tarixga saqlash
        database.add_history_item(api_user["id"], file_path, json.dumps(result_json))

        return result_json

    except Exception as e:
        return JSONResponse(status_code=500, content={"error": f"Tahlil jarayonida xatolik: {str(e)}"})
