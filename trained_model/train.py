import os
import torch
from PIL import Image
from transformers import CLIPProcessor, CLIPModel
import chromadb
from dotenv import load_dotenv
from tqdm import tqdm

load_dotenv()

MODEL_NAME = os.getenv("IMAGE_EMBEDDING_MODEL", "openai/clip-vit-base-patch32")

# Initialize CLIP
print(f"Loading model: {MODEL_NAME}...")
device = "cuda" if torch.cuda.is_available() else "cpu"
model = CLIPModel.from_pretrained(MODEL_NAME).to(device)
processor = CLIPProcessor.from_pretrained(MODEL_NAME)

# Initialize ChromaDB
client = chromadb.PersistentClient(path="./chroma_db_kvasir_v1")
collection = client.get_or_create_collection(
    name="endoscopy",
    metadata={"hnsw:space": "cosine"}
)

def get_image_embedding(image_path):
    image = Image.open(image_path).convert("RGB")
    inputs = processor(images=image, return_tensors="pt").to(device)
    with torch.no_grad():
        outputs = model.get_image_features(**inputs)
        
    # Handle different output formats (BaseModelOutputWithPooling, CLIPOutput, or Tensor)
    if isinstance(outputs, torch.Tensor):
        image_features = outputs
    elif hasattr(outputs, "pooler_output") and outputs.pooler_output is not None:
        image_features = outputs.pooler_output
    elif hasattr(outputs, "image_embeds") and outputs.image_embeds is not None:
        image_features = outputs.image_embeds
    else:
        # Fallback to first element if it's a tuple or similar
        image_features = outputs[0] if isinstance(outputs, (list, tuple)) else outputs

    # Normalize embedding
    image_features = image_features / image_features.norm(p=2, dim=-1, keepdim=True)
    return image_features.cpu().numpy().flatten().tolist()

def train():
    # Use dataset as confirmed by directory listing
    train_dir = "dataset/kvasir-dataset-v2"

    diseases = [d for d in os.listdir(train_dir) if os.path.isdir(os.path.join(train_dir, d))]
    
    for disease in diseases:
        brand_path = os.path.join(train_dir, disease)
        print(f"\nProcessing disease: {disease}")
        
        # Support common image formats
        image_files = [f for f in os.listdir(brand_path) if f.lower().endswith(('.png', '.jpg', '.jpeg', '.webp'))]
        
        # To avoid overloading memory/DB, we can batch process or just loop
        for img_name in tqdm(image_files, desc=f"Embedding {disease}"):
            img_path = os.path.join(brand_path, img_name)
            try:
                embedding = get_image_embedding(img_path)
                collection.add(
                    ids=[f"{disease}_{img_name}"],
                    embeddings=[embedding],
                    metadatas=[{"disease": disease}],
                    documents=[img_path]
                )
            except Exception as e:
                print(f"Error processing {img_path}: {e}")

if __name__ == "__main__":
    train()
    print("\nTraining completed. Vector database saved in ./chroma_db_kvasir_v1")
