#!/usr/bin/env python3
"""
Enhanced KB Chunks Rebuilder
Regenerates embeddings for existing metadata with improved efficiency and reliability
"""

import os
import pickle
import time
import json
from datetime import datetime
from typing import List, Dict, Any
import numpy as np
from dotenv import load_dotenv
from openai import OpenAI
from tenacity import retry, stop_after_attempt, wait_exponential
import logging

# Setup
load_dotenv()
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class KBChunksRebuilder:
    def __init__(self, 
                 metadata_file: str = "metadata.pkl",
                 output_file: str = "kb_chunks/kb_chunks.pkl",
                 embedding_model: str = "text-embedding-3-small",
                 batch_size: int = 20,
                 max_retries: int = 3):
        """
        Initialize the rebuilder with configuration
        
        Args:
            metadata_file: Path to metadata pickle file
            output_file: Path to output kb_chunks pickle file
            embedding_model: OpenAI embedding model to use
            batch_size: Number of texts to embed in one API call
            max_retries: Maximum retries for failed embeddings
        """
        self.metadata_file = metadata_file
        self.output_file = output_file
        self.embedding_model = embedding_model
        self.batch_size = batch_size
        self.max_retries = max_retries
        
        # Initialize OpenAI client
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("OPENAI_API_KEY not found in environment variables")
        self.client = OpenAI(api_key=api_key)
        
        # Statistics
        self.stats = {
            "total_chunks": 0,
            "successful_embeddings": 0,
            "failed_embeddings": 0,
            "skipped_chunks": 0,
            "api_calls": 0,
            "start_time": None,
            "end_time": None
        }
    
    def load_metadata(self) -> List[Dict]:
        """Load metadata from pickle file"""
        if not os.path.exists(self.metadata_file):
            raise FileNotFoundError(f"Metadata file not found: {self.metadata_file}")
        
        with open(self.metadata_file, "rb") as f:
            metadata = pickle.load(f)
        
        logger.info(f"Loaded {len(metadata)} chunks from {self.metadata_file}")
        return metadata
    
    def extract_text(self, chunk: Dict) -> str:
        """Extract text from chunk, handling different field names"""
        text = chunk.get("text") or chunk.get("chunk") or chunk.get("content")
        if not text:
            logger.warning(f"No text field found in chunk: {chunk.keys()}")
            return None
        return text.strip()
    
    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
    def generate_embeddings_batch(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings for a batch of texts with retry logic"""
        try:
            response = self.client.embeddings.create(
                model=self.embedding_model,
                input=texts
            )
            self.stats["api_calls"] += 1
            return [data.embedding for data in response.data]
        except Exception as e:
            logger.error(f"Batch embedding failed: {e}")
            raise
    
    def process_chunks(self, metadata: List[Dict]) -> List[Dict]:
        """Process all chunks and add embeddings"""
        kb_chunks = []
        failed_chunks = []
        
        # Process in batches
        for i in range(0, len(metadata), self.batch_size):
            batch_metadata = metadata[i:i + self.batch_size]
            batch_texts = []
            batch_indices = []
            
            # Prepare batch
            for j, chunk in enumerate(batch_metadata):
                text = self.extract_text(chunk)
                if text:
                    batch_texts.append(text)
                    batch_indices.append(j)
                else:
                    self.stats["skipped_chunks"] += 1
                    logger.warning(f"Skipping chunk {i+j}: No text content")
            
            if not batch_texts:
                continue
            
            # Generate embeddings for batch
            try:
                embeddings = self.generate_embeddings_batch(batch_texts)
                
                # Add embeddings to chunks
                for idx, embedding in zip(batch_indices, embeddings):
                    chunk = batch_metadata[idx].copy()
                    chunk["embedding"] = embedding
                    kb_chunks.append(chunk)
                    self.stats["successful_embeddings"] += 1
                
                # Progress update
                progress = len(kb_chunks) / len(metadata) * 100
                logger.info(f"Progress: {len(kb_chunks)}/{len(metadata)} chunks ({progress:.1f}%)")
                
                # Rate limiting
                time.sleep(0.5)
                
            except Exception as e:
                logger.error(f"Failed to process batch {i//self.batch_size}: {e}")
                self.stats["failed_embeddings"] += len(batch_texts)
                failed_chunks.extend(batch_metadata)
                
                # Try individual processing for failed batch
                for j, text in enumerate(batch_texts):
                    try:
                        response = self.client.embeddings.create(
                            model=self.embedding_model,
                            input=text
                        )
                        chunk = batch_metadata[batch_indices[j]].copy()
                        chunk["embedding"] = response.data[0].embedding
                        kb_chunks.append(chunk)
                        self.stats["successful_embeddings"] += 1
                        self.stats["failed_embeddings"] -= 1
                        time.sleep(1)  # Extra delay for individual calls
                    except Exception as e2:
                        logger.error(f"Individual embedding also failed: {e2}")
        
        return kb_chunks, failed_chunks
    
    def save_chunks(self, kb_chunks: List[Dict]):
        """Save chunks to pickle file"""
        # Create directory if needed
        os.makedirs(os.path.dirname(self.output_file), exist_ok=True)
        
        # Save pickle file
        with open(self.output_file, "wb") as f:
            pickle.dump(kb_chunks, f)
        
        logger.info(f"Saved {len(kb_chunks)} chunks to {self.output_file}")
        
        # Also save as JSON for inspection
        json_file = self.output_file.replace('.pkl', '.json')
        chunks_for_json = []
        for chunk in kb_chunks:
            chunk_copy = chunk.copy()
            # Convert embedding to list for JSON serialization
            if "embedding" in chunk_copy and isinstance(chunk_copy["embedding"], np.ndarray):
                chunk_copy["embedding"] = chunk_copy["embedding"].tolist()
            chunks_for_json.append(chunk_copy)
        
        with open(json_file, "w", encoding="utf-8") as f:
            json.dump({
                "metadata": {
                    "total_chunks": len(chunks_for_json),
                    "embedding_model": self.embedding_model,
                    "created_at": datetime.now().isoformat()
                },
                "chunks": chunks_for_json
            }, f, indent=2, ensure_ascii=False)
        
        logger.info(f"Also saved JSON version to {json_file}")
    
    def save_failed_chunks(self, failed_chunks: List[Dict]):
        """Save failed chunks for manual inspection"""
        if not failed_chunks:
            return
        
        failed_file = "failed_chunks.pkl"
        with open(failed_file, "wb") as f:
            pickle.dump(failed_chunks, f)
        
        logger.warning(f"Saved {len(failed_chunks)} failed chunks to {failed_file}")
    
    def print_summary(self):
        """Print processing summary"""
        duration = (self.stats["end_time"] - self.stats["start_time"]).total_seconds()
        
        print("\n" + "="*50)
        print("REBUILD SUMMARY")
        print("="*50)
        print(f"Total chunks processed: {self.stats['total_chunks']}")
        print(f"Successful embeddings: {self.stats['successful_embeddings']}")
        print(f"Failed embeddings: {self.stats['failed_embeddings']}")
        print(f"Skipped chunks: {self.stats['skipped_chunks']}")
        print(f"API calls made: {self.stats['api_calls']}")
        print(f"Processing time: {duration:.2f} seconds")
        print(f"Average time per chunk: {duration/self.stats['total_chunks']:.2f} seconds")
        
        if self.stats['api_calls'] > 0:
            avg_batch_size = self.stats['successful_embeddings'] / self.stats['api_calls']
            print(f"Average batch size: {avg_batch_size:.1f} chunks/call")
        
        # Estimate cost (approximate)
        tokens_estimate = self.stats['successful_embeddings'] * 500  # Rough estimate
        cost_estimate = (tokens_estimate / 1_000_000) * 0.02  # $0.02 per 1M tokens for ada-002
        print(f"Estimated API cost: ${cost_estimate:.4f}")
        print("="*50)
    
    def rebuild(self):
        """Main rebuild process"""
        self.stats["start_time"] = datetime.now()
        
        try:
            # Load metadata
            metadata = self.load_metadata()
            self.stats["total_chunks"] = len(metadata)
            
            # Check for existing embeddings
            existing_with_embeddings = sum(1 for chunk in metadata if "embedding" in chunk)
            if existing_with_embeddings > 0:
                logger.warning(f"Found {existing_with_embeddings} chunks with existing embeddings")
                response = input("Do you want to regenerate all embeddings? (y/n): ")
                if response.lower() != 'y':
                    # Filter out chunks with embeddings
                    metadata = [chunk for chunk in metadata if "embedding" not in chunk]
                    logger.info(f"Processing {len(metadata)} chunks without embeddings")
            
            if not metadata:
                logger.info("No chunks to process")
                return
            
            # Process chunks
            kb_chunks, failed_chunks = self.process_chunks(metadata)
            
            # Save results
            self.save_chunks(kb_chunks)
            self.save_failed_chunks(failed_chunks)
            
        except Exception as e:
            logger.error(f"Rebuild failed: {e}")
            raise
        
        finally:
            self.stats["end_time"] = datetime.now()
            self.print_summary()

def main():
    """Main entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Rebuild KB chunks with embeddings")
    parser.add_argument("--metadata", default="metadata.pkl", help="Input metadata file")
    parser.add_argument("--output", default="kb_chunks/kb_chunks.pkl", help="Output KB chunks file")
    parser.add_argument("--model", default="text-embedding-3-small", help="Embedding model")
    parser.add_argument("--batch-size", type=int, default=20, help="Batch size for embeddings")
    parser.add_argument("--max-retries", type=int, default=3, help="Max retries for failed embeddings")
    
    args = parser.parse_args()
    
    rebuilder = KBChunksRebuilder(
        metadata_file=args.metadata,
        output_file=args.output,
        embedding_model=args.model,
        batch_size=args.batch_size,
        max_retries=args.max_retries
    )
    
    rebuilder.rebuild()

if __name__ == "__main__":
    main()
