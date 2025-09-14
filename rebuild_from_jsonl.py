#!/usr/bin/env python3
"""
Rebuild KB chunks from chunks.jsonl file with proper embeddings
"""

import os
import json
import pickle
import time
from datetime import datetime
from typing import List, Dict, Any
import numpy as np
from dotenv import load_dotenv
from openai import OpenAI
import logging

# Setup
load_dotenv()
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def rebuild_from_jsonl():
    """Rebuild KB chunks from chunks.jsonl with correct embeddings"""
    
    # Initialize OpenAI client
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise ValueError("OPENAI_API_KEY not found in environment variables")
    client = OpenAI(api_key=api_key)
    
    # Find chunks.jsonl file
    jsonl_file = None
    for path in ["kb_chunks/chunks.jsonl", "chunks.jsonl", "data/chunks.jsonl"]:
        if os.path.exists(path):
            jsonl_file = path
            break
    
    if not jsonl_file:
        logger.error("Could not find chunks.jsonl file")
        return
    
    logger.info(f"Loading chunks from: {jsonl_file}")
    
    # Load chunks from JSONL
    chunks = []
    with open(jsonl_file, 'r', encoding='utf-8') as f:
        for line_num, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue
            try:
                chunk = json.loads(line)
                chunks.append(chunk)
            except json.JSONDecodeError as e:
                logger.warning(f"Failed to parse line {line_num}: {e}")
                continue
    
    logger.info(f"Loaded {len(chunks)} chunks from JSONL")
    
    # Verify chunks have text
    chunks_with_text = [chunk for chunk in chunks if chunk.get('text', '').strip()]
    logger.info(f"Found {len(chunks_with_text)} chunks with text content")
    
    if not chunks_with_text:
        logger.error("No chunks with text content found!")
        return
    
    # Process chunks in batches
    batch_size = 20
    kb_chunks = []
    failed_chunks = []
    
    logger.info("Starting embedding generation...")
    
    for i in range(0, len(chunks_with_text), batch_size):
        batch = chunks_with_text[i:i + batch_size]
        batch_texts = [chunk["text"] for chunk in batch]
        
        try:
            batch_num = i // batch_size + 1
            total_batches = (len(chunks_with_text) + batch_size - 1) // batch_size
            logger.info(f"Processing batch {batch_num}/{total_batches} ({len(batch_texts)} chunks)")
            
            # Generate embeddings
            response = client.embeddings.create(
                model="text-embedding-3-small",
                input=batch_texts
            )
            
            # Create KB chunks with embeddings
            for j, (chunk, embedding_data) in enumerate(zip(batch, response.data)):
                kb_chunk = {
                    "id": len(kb_chunks),
                    "text": chunk["text"],
                    "url": chunk["url"],
                    "embedding": embedding_data.embedding,
                    "metadata": {
                        "len": len(chunk["text"].split()),
                        "chunk_index": len(kb_chunks),
                        "source_type": "html",  # Adjust based on your data
                        "original_index": i + j
                    }
                }
                kb_chunks.append(kb_chunk)
            
            # Progress update
            progress = len(kb_chunks) / len(chunks_with_text) * 100
            logger.info(f"Progress: {len(kb_chunks)}/{len(chunks_with_text)} chunks ({progress:.1f}%)")
            
            # Rate limiting
            time.sleep(0.5)
            
        except Exception as e:
            logger.error(f"Failed to process batch {batch_num}: {e}")
            failed_chunks.extend(batch)
            continue
    
    logger.info(f"Successfully created {len(kb_chunks)} KB chunks")
    
    # Save KB chunks
    os.makedirs("kb_chunks", exist_ok=True)
    output_file = "kb_chunks/kb_chunks.pkl"
    
    with open(output_file, "wb") as f:
        pickle.dump(kb_chunks, f)
    
    logger.info(f"Saved KB chunks to: {output_file}")
    
    # Verify embeddings
    if kb_chunks:
        embeddings_array = np.array([chunk["embedding"] for chunk in kb_chunks])
        logger.info(f"Final embeddings shape: {embeddings_array.shape}")
        logger.info(f"Embedding dimensions: {embeddings_array.shape[1]}")
    
    # Save failed chunks if any
    if failed_chunks:
        with open("failed_chunks.pkl", "wb") as f:
            pickle.dump(failed_chunks, f)
        logger.warning(f"Saved {len(failed_chunks)} failed chunks")
    
    # Create summary
    logger.info("=" * 50)
    logger.info("REBUILD SUMMARY")
    logger.info("=" * 50)
    logger.info(f"Total input chunks: {len(chunks)}")
    logger.info(f"Chunks with text: {len(chunks_with_text)}")
    logger.info(f"Successfully processed: {len(kb_chunks)}")
    logger.info(f"Failed chunks: {len(failed_chunks)}")
    logger.info(f"Final embedding dimensions: {embeddings_array.shape[1] if kb_chunks else 'N/A'}")
    logger.info("=" * 50)
    
    logger.info("Rebuild complete! Your knowledge base should now work properly.")

if __name__ == "__main__":
    rebuild_from_jsonl()
