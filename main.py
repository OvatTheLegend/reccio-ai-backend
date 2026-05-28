import json
import os
from dotenv import load_dotenv
from fastapi import FastAPI
from pydantic import BaseModel
from openai import OpenAI

load_dotenv()

api_key = os.getenv("OPENAI_API_KEY")
ai_model = os.getenv("OPENAI_MODEL")

def check_ai_config():
    if not api_key:
        return "Chýba OPENAI_API_KEY v .env súbore."
    
    if not ai_model:
        return "Chýba OPENAI_MODEL v .env súbore."
    
    return None

client = OpenAI(api_key=api_key) if api_key else None
app = FastAPI()


class ParseReceiptTextRequest(BaseModel):
    text: str


class ParseReceiptImageRequest(BaseModel):
    image_base64: str
    media_type: str


class CategorizeItemsRequest(BaseModel):
    items: list

@app.get("/")
def root():
    return {
        "success": True,
        "message": "AI backend bezi"
    }


@app.post("/parse-receipt-text")
def parse_receipt_text(data: ParseReceiptTextRequest):
    
    config_error = check_ai_config()
    if config_error:
        return {
            "success": False,
            "error": "missing_ai_config",
            "message": config_error
        }
    
    prompt = f"""
    Toto je pokladničný blok.
    Ak vstup neobsahuje pokladničný blok alebo z neho nevieš spoľahlivo určiť obchod, dátum, celkovú sumu a položky nákupu, nevymýšľaj údaje a vráť ONLY tento JSON:
    {{
        "success": false,
        "message": "Daný súbor neobsahuje údaje o pokladničnom bloku."
    }}
    Extrahuj z neho tieto údaje a vráť ONLY JSON bez akéhokoľvek iného textu:
    {{
        "shop_name": "názov obchodu",
        "date": "DD.MM.YYYY",
        "time": "HH:MM:SS",
        "price": 0.00,
        "items": [
            {{
                "item_name": "názov položky",
                "amount": "pocet položiek",
                "price": "cena položky",
                "category": "kategoria položky"
            }}
        ]
    }}
    Pravidlá su nasledovné:
    - shop_name je nazov obchody, teda TERNO, TESCO, KAUFLAND atd...
    - date musí byť formát DD.MM.YYYY
    - time musí byť formát HH:MM:SS
    - price je celková suma nakupu ako float cislo
    - items sú jednotlivé položky, ak je samostnatna položka nejaka zlava, teda napriklad seniorska zlava -4.30 tak tieto neposielaj, iba položky ktore sme kupili a maju kladnu sumu.
    - item_name je celý nazov položky
    - amount je počet kupených kusov, teda napriklad pri kuracich prsiach to moze byt aj 0.675
    - price je cena danej položky
    - category je kategoria položky musis vybrat jednu z: "Potraviny", "Drogéria", "Lieky", "Elektronika", "Oblečenie", "Ostatné",
    - vitaminy a vyzivove doplnky považuj za lieky
    - hocijake jedlo, ci už to je tycinka, alebo su to chrumky, čipsy -> zarad ako Potraviny
    - takisto hocijake pitie, dzus, vodka, pivo, voda, preliva voda magnesium atd -> zarad ako potraviny
    - Ak budes ukladat mená obchodov tak, špecificky tieto obchody uloz takto, teda napriklad ked bude dr max -> Dr.Max, teda bez medzeri:
    -> Dr.Max (pre dr max)
    -> TERNO (pre terno)
    -> DM (pre drogeriu dm)
    -> KAUFLAND (pre kaufland)
    text blocku:    
    {data.text}
    """
    
    #skusime odoslat
    try:
        response = client.chat.completions.create(
            model=ai_model,
            messages=[
                {
                "role": "user", 
                "content": prompt
                }
            ],
            max_tokens=2500,
        )

        ai_result = response.choices[0].message.content.strip()

        #odstranime obalenie json bloku
        ai_result = ai_result.replace("```json", "").replace("```", "").strip()

        data = json.loads(ai_result)
        if data.get("success") is False:
            return {
                "success": False,
                "error": "not_receipt",
                "message": data.get("message", "Daný súbor neobsahuje údaje o pokladničnom bloku.")
            }
        
        return {"success": True, "data": data}

    except json.JSONDecodeError as e:
        print(f"AI vratilo neplatny JSON: {e}")
        return {"success": False, "message": "..."}
        
    except Exception as e:
        print(f"AI parser chyba: {e}")
        return {"success": False, "message": "..."}

@app.post("/parse-receipt-image")
def parse_receipt_image(data: ParseReceiptImageRequest):

    config_error = check_ai_config()
    if config_error:
        return {
            "success": False,
            "error": "missing_ai_config",
            "message": config_error
        }

    prompt = f"""
    Toto je pokladničný blok.
    Ak vstup neobsahuje pokladničný blok alebo z neho nevieš spoľahlivo určiť obchod, dátum, celkovú sumu a položky nákupu, nevymýšľaj údaje a vráť ONLY tento JSON:
    {{
        "success": false,
        "message": "Daný súbor neobsahuje údaje o pokladničnom bloku."
    }}
    Extrahuj z neho tieto údaje a vráť ONLY JSON bez akéhokoľvek iného textu:
    {{
        "shop_name": "názov obchodu",
        "date": "DD.MM.YYYY",
        "time": "HH:MM:SS",
        "price": 0.00,
        "items": [
            {{
                "item_name": "názov položky",
                "amount": "pocet položiek",
                "price": "cena položky",
                "category": "kategoria položky"
            }}
        ]
    }}
    Pravidlá su nasledovné:
    - shop_name je nazov obchody, teda TERNO, TESCO, KAUFLAND atd...
    - date musí byť formát DD.MM.YYYY
    - time musí byť formát HH:MM:SS
    - price je celková suma nakupu ako float cislo
    - items sú jednotlivé položky, ak je samostnatna položka nejaka zlava, teda napriklad seniorska zlava -4.30 tak tieto neposielaj, iba položky ktore sme kupili a maju kladnu sumu.
    - item_name je celý nazov položky
    - amount je počet kupených kusov, teda napriklad pri kuracich prsiach to moze byt aj 0.675
    - price je cena danej položky
    - category je kategoria položky musis vybrat jednu z: "Potraviny", "Drogéria", "Lieky", "Elektronika", "Oblečenie", "Ostatné",
    - vitaminy a vyzivove doplnky považuj za lieky
    - hocijake jedlo, ci už to je tycinka, alebo su to chrumky, čipsy -> zarad ako Potraviny
    - takisto hocijake pitie, čaje , dzus, vodka, pivo, voda, preliva voda magnesium atd -> zarad ako potraviny
    - Ak budes ukladat mená obchodov tak, špecificky tieto obchody uloz takto, teda napriklad ked bude dr max -> Dr.Max, teda bez medzeri:
    -> Dr.Max (pre dr max)
    -> Dr.Max (pre dr max)
    -> TERNO (pre terno)
    -> DM (pre drogeriu dm)
    -> KAUFLAND (pre kaufland)
    """
    
    #skusime odoslat
    try:
        response = client.chat.completions.create(
            model=ai_model,
            messages=[
                {
                "role": "user", 
                "content": [
                    {
                        "type" : "image_url",
                        "image_url" : {
                            "url" : f'data:{data.media_type};base64,{data.image_base64}'
                        }
                    },
                    {
                        "type" : "text",
                        "text" : prompt
                    }
                ]
                }
            ],
            max_tokens=1000,
        )

        ai_result = response.choices[0].message.content.strip()

        #odstranime obalenie json bloku
        ai_result = ai_result.replace("```json", "").replace("```", "").strip()
        
        start = ai_result.find("{")
        end = ai_result.rfind("}")
        if start != -1 and end != -1:
            ai_result = ai_result[start:end+1]

        data = json.loads(ai_result)
        if data.get("success") is False:
            return {
                "success": False,
                "error": "not_receipt",
                "message": data.get("message", "Daný súbor neobsahuje údaje o pokladničnom bloku.")
            }
        
        return {"success": True, "data": data}

    except json.JSONDecodeError as e:
        print(f"AI vratilo neplatny JSON: {e}")
        return {"success": False, "message": "..."}
        
    except Exception as e:
        print(f"AI parser chyba: {e}")
        return {"success": False, "message": "..."}


@app.post("/categorize-items")
def categorize_items(data: CategorizeItemsRequest):

    config_error = check_ai_config()
    if config_error:
        return {
            "success": False,
            "error": "missing_ai_config",
            "message": config_error
        }
        
    items_for_prompt = []

    for item in data.items:
        items_for_prompt.append({
            "id": item["id"],
            "item_name": item["item_name"]
        })

    #prompt
    prompt = f"""
    Toto su položky z pokladničného bloku, tvojou ulohou je urcit kategoriiu danej položky, nižšie su povolene kategorie a pravidla uvedene.
    VRÁŤ IBA ČISTÉ JSON POLE.
    NEPÍŠ žiadny úvod, vysvetlenie ani markdown.
    
    Pravidlá su nasledovné:

    - category je kategoria položky musis vybrat jednu z: "Potraviny", "Drogéria", "Lieky", "Elektronika", "Oblečenie", "Ostatné",
    - vitaminy a vyzivove doplnky považuj za lieky
    - hocijake jedlo, ci už to je tycinka, alebo su to chrumky, čipsy -> zarad ako Potraviny
    - takisto hocijake pitie, čaje, dzus, vodka, pivo, voda, preliva voda magnesium atd -> zarad ako potraviny
    - každá položka musi mať presne priradene id,category

    položky:
    {json.dumps(items_for_prompt, ensure_ascii=False)}
    """

    try:
        response = client.chat.completions.create(
            model=ai_model,
            messages=[
                {
                "role": "user", 
                "content": prompt
                }
            ],
            max_tokens=700,
        )

        ai_result = response.choices[0].message.content.strip()

        #odstranime obalenie json bloku
        ai_result = ai_result.replace("```json", "").replace("```", "").strip()

        #este pre istotu takto
        start = ai_result.find("[")
        end = ai_result.rfind("]")
        if start != -1 and end != -1:
            ai_result = ai_result[start:end+1]

        data = json.loads(ai_result)

        return_data = []

        for item in data:
            #ak nahodou nieco chyba tak skip
            if "id" not in item or "category" not in item:
                continue

            return_data.append({
                "id": item["id"],
                "category" : item["category"]
            })
            
        return {"success": True, "items": return_data}

    except json.JSONDecodeError as e:
        print(f"AI vratilo neplatny JSON: {e}")
        return {"success": False, "message": "..."}
        
    except Exception as e:
        print(f"AI parser chyba: {e}")
        return {"success": False, "message": "..."}
    
