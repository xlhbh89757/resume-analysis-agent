"""模型下载脚本"""
import sys
import os
from pathlib import Path


def download_qwen_model():
    """下载 Qwen 模型"""
    print("Downloading Qwen model...")
    print("This may take a while depending on your internet speed.")
    print()
    
    try:
        from huggingface_hub import snapshot_download
        
        model_name = "Qwen/Qwen2.5-14B-Instruct"
        local_dir = Path("./models") / model_name.replace("/", "_")
        local_dir.mkdir(parents=True, exist_ok=True)
        
        print(f"Model: {model_name}")
        print(f"Local directory: {local_dir}")
        print()
        
        snapshot_download(
            repo_id=model_name,
            local_dir=str(local_dir),
            resume_download=True,
        )
        
        print(f"\nModel downloaded successfully to: {local_dir}")
        print(f"\nUpdate your .env file with:")
        print(f"LOCAL_MODEL_PATH={local_dir.absolute()}")
        
    except ImportError:
        print("Please install huggingface_hub first:")
        print("  pip install huggingface_hub")
        sys.exit(1)
    except Exception as e:
        print(f"Failed to download model: {e}")
        sys.exit(1)


def download_embedding_model():
    """下载 Embedding 模型"""
    print("\nDownloading embedding model...")
    
    try:
        from fastembed import TextEmbedding
        
        model_name = "BAAI/bge-m3"
        print(f"Model: {model_name}")
        
        # 初始化会自动下载模型
        _ = TextEmbedding(model_name)
        
        print("Embedding model downloaded successfully!")
        
    except ImportError:
        print("Please install fastembed first:")
        print("  pip install fastembed")
    except Exception as e:
        print(f"Failed to download embedding model: {e}")


def main():
    print("=" * 50)
    print("Resume Agent - Model Download Script")
    print("=" * 50)
    print()
    
    choice = input("Which model to download?\n1. Qwen LLM model\n2. Embedding model (BGE-M3)\n3. Both\n\nEnter choice (1/2/3): ").strip()
    
    if choice == "1":
        download_qwen_model()
    elif choice == "2":
        download_embedding_model()
    elif choice == "3":
        download_qwen_model()
        download_embedding_model()
    else:
        print("Invalid choice")
        sys.exit(1)


if __name__ == "__main__":
    main()
