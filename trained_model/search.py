import os
import logging
import warnings
import sys
import torch
from PIL import Image
from transformers import CLIPProcessor, CLIPModel
import chromadb
from dotenv import load_dotenv

load_dotenv()

# 1. Hugging Face log darajasini faqat xatoliklar (ERROR) uchun sozlash
os.environ["HF_HUB_DISABLE_SYMLINKS_WARNING"] = "1"
os.environ["TRANSFORMERS_VERBOSITY"] = "error"

# 2. PyTorch va boshqa kutubxonalarning ogohlantirishlarini yashirish
warnings.filterwarnings("ignore")

# 3. Standard logging tizimini o'chirish
logging.getLogger("transformers").setLevel(logging.ERROR)

MODEL_NAME = os.getenv("IMAGE_EMBEDDING_MODEL", "openai/clip-vit-base-patch32")

# Initialize CLIP
print(f"Loading model: {MODEL_NAME}...")
device = "cuda" if torch.cuda.is_available() else "cpu"
model = CLIPModel.from_pretrained(MODEL_NAME).to(device)
processor = CLIPProcessor.from_pretrained(MODEL_NAME)

# Initialize ChromaDB
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(CURRENT_DIR, "chroma_db_kvasir_v1")
client = chromadb.PersistentClient(path=DB_PATH)

try:
    collection = client.get_collection(name="endoscopy")
except Exception:
    print(f"Error: Vector database not found at {DB_PATH}. Please run train.py first.")
    # In a production app, we might not want to exit here if imported
    if __name__ == "__main__":
        sys.exit(1)
    else:
        collection = None

def get_image_embedding(image_path):
    image = Image.open(image_path).convert("RGB")
    inputs = processor(images=image, return_tensors="pt").to(device)
    with torch.no_grad():
        outputs = model.get_image_features(**inputs)
        
    # Handle different output formats
    if isinstance(outputs, torch.Tensor):
        image_features = outputs
    elif hasattr(outputs, "pooler_output") and outputs.pooler_output is not None:
        image_features = outputs.pooler_output
    elif hasattr(outputs, "image_embeds") and outputs.image_embeds is not None:
        image_features = outputs.image_embeds
    else:
        image_features = outputs[0] if isinstance(outputs, (list, tuple)) else outputs

    # Normalize embedding
    image_features = image_features / image_features.norm(p=2, dim=-1, keepdim=True)
    return image_features.cpu().numpy().flatten().tolist()

def search(image_path):
    if not os.path.exists(image_path):
        return {"error": f"File {image_path} not found."}

    if collection is None:
        return {"error": "Vector database not initialized."}

    try:
        embedding = get_image_embedding(image_path)
        results = collection.query(
            query_embeddings=[embedding],
            n_results=1
        )
        
        if results['ids'] and results['ids'][0]:
            disease = results['metadatas'][0][0]['disease']
            # Distance for cosine is 1 - similarity. So similarity = 1 - distance.
            distance = results['distances'][0][0]
            confidence = (1 - distance) * 100
            
            # Ensure confidence doesn't exceed 100% or go below 0%
            confidence = max(0.0, min(100.0, confidence))
            
            return {
                "disease": disease,
                "confidence": round(confidence, 2),
                "matched_image": results['documents'][0][0] if results['documents'] else None
            }
        else:
            return {"error": "No match found."}
    except Exception as e:
        return {"error": f"Error during search: {str(e)}"}

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python search.py <image_path>")
    else:
        res = search(sys.argv[1])
        print(res)
