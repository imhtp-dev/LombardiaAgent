"""
Q&A Management endpoints with Pinecone integration
"""

from fastapi import APIRouter, HTTPException, Depends
from typing import List
import os
import time
from loguru import logger
from pinecone import Pinecone
from openai import OpenAI

from .database import db
from .models import (
    QACreate,
    QAUpdate,
    QAItem,
    QACreateResponse,
    QAUpdateResponse,
    QADeleteResponse,
    QAStatsResponse
)
from .utils import get_italy_time_naive, generate_pinecone_id
from .auth import get_current_user_from_token


router = APIRouter()


# ==================== Pinecone & OpenAI Initialization ====================

pinecone_client = None
pinecone_index = None
openai_client = None


def initialize_ai_services():
    """Initialize Pinecone and OpenAI clients"""
    global pinecone_client, pinecone_index, openai_client
    
    try:
        # Initialize Pinecone
        pinecone_api_key = os.getenv("PINECONE_API_KEY")
        if pinecone_api_key:
            pinecone_client = Pinecone(api_key=pinecone_api_key)
            pinecone_index = pinecone_client.Index(
                "knowledgecerba",
                host="https://knowledgecerba-eqvpxqp.svc.apu-57e2-42f6.pinecone.io"
            )
            logger.info("✅ Pinecone client initialized (knowledgecerba)")
        else:
            logger.warning("⚠️ PINECONE_API_KEY not set")
        
        # Initialize OpenAI
        openai_api_key = os.getenv("OPENAI_API_KEY")
        if openai_api_key:
            openai_client = OpenAI(api_key=openai_api_key)
            logger.info("✅ OpenAI client initialized")
        else:
            logger.warning("⚠️ OPENAI_API_KEY not set")
            
    except Exception as e:
        logger.error(f"❌ Error initializing AI services: {e}")


# ==================== Helper Functions ====================

def get_embedding(text: str, max_retries: int = 3) -> List[float]:
    """
    Generate embedding using OpenAI
    
    Args:
        text: Text to embed
        max_retries: Maximum retry attempts
    
    Returns:
        Embedding vector (1024 dimensions)
    """
    if not openai_client:
        raise HTTPException(
            status_code=500,
            detail="OpenAI client not initialized"
        )
    
    for attempt in range(max_retries):
        try:
            response = openai_client.embeddings.create(
                model="text-embedding-3-large",
                input=text.strip(),
                dimensions=1024
            )
            
            embedding = response.data[0].embedding
            logger.info(f"✅ Generated embedding, length: {len(embedding)}")
            return embedding
            
        except Exception as e:
            logger.warning(f"⚠️ Embedding attempt {attempt + 1} failed: {e}")
            if attempt == max_retries - 1:
                logger.error(f"❌ All embedding attempts failed")
                raise HTTPException(
                    status_code=500,
                    detail=f"Errore generazione embedding: {str(e)}"
                )
            time.sleep(1)


async def save_to_pinecone(qa_id: int, question: str, answer: str, region: str) -> str:
    """
    Save Q&A to Pinecone
    
    Args:
        qa_id: Q&A ID from database
        question: Question text
        answer: Answer text
        region: Region name
    
    Returns:
        Pinecone ID
    """
    try:
        if not pinecone_index:
            raise HTTPException(
                status_code=500,
                detail="Pinecone index not initialized"
            )
        
        logger.info(f"💾 Saving to Pinecone: QA ID {qa_id}")
        
        # Generate embedding
        embedding = get_embedding(question)
        
        # Generate unique ID
        pinecone_id = generate_pinecone_id(region, qa_id)
        
        # Create vector
        vector = {
            'id': pinecone_id,
            'values': embedding,
            'metadata': {
                'question': question,
                'answer': answer,
                'regione': region,  # Pinecone uses 'regione' (Italian), Supabase uses 'region'
                'qa_id': qa_id,
                'created_at': get_italy_time_naive().isoformat()
            }
        }
        
        # Upsert to Pinecone
        response = pinecone_index.upsert(vectors=[vector])
        logger.info(f"✅ Saved to Pinecone: {pinecone_id}")
        
        return pinecone_id
        
    except Exception as e:
        logger.error(f"❌ Error saving to Pinecone: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Errore salvataggio Pinecone: {str(e)}"
        )


async def update_pinecone(
    pinecone_id: str,
    question: str,
    answer: str,
    region: str,
    qa_id: int
) -> str:
    """
    Update Pinecone vector (delete old, create new)
    
    Args:
        pinecone_id: Old Pinecone ID
        question: New question text
        answer: New answer text
        region: Region name
        qa_id: Q&A ID from database
    
    Returns:
        New Pinecone ID
    """
    try:
        if not pinecone_index:
            raise HTTPException(
                status_code=500,
                detail="Pinecone index not initialized"
            )
        
        logger.info(f"🔄 Updating Pinecone: {pinecone_id}")
        
        # Delete old vector
        if pinecone_id:
            pinecone_index.delete(ids=[pinecone_id])
            logger.info(f"✅ Deleted old vector: {pinecone_id}")
        
        # Create new vector
        new_pinecone_id = await save_to_pinecone(qa_id, question, answer, region)
        
        return new_pinecone_id
        
    except Exception as e:
        logger.error(f"❌ Error updating Pinecone: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Errore aggiornamento Pinecone: {str(e)}"
        )


async def delete_from_pinecone(pinecone_id: str):
    """
    Delete vector from Pinecone
    
    Args:
        pinecone_id: Pinecone ID to delete
    """
    try:
        if not pinecone_index:
            logger.warning("⚠️ Pinecone index not initialized, skipping deletion")
            return
        
        if pinecone_id:
            response = pinecone_index.delete(ids=[pinecone_id])
            logger.info(f"✅ Deleted from Pinecone: {pinecone_id}")
        
    except Exception as e:
        logger.error(f"❌ Error deleting from Pinecone: {e}")
        # Don't raise exception for delete failures


async def generate_next_id_domanda() -> str:
    """
    Generate next id_domanda in format N0XXX
    
    Returns:
        New id_domanda (e.g., "N0001", "N0002", etc.)
    """
    try:
        logger.info("🔢 Generating next id_domanda")
        
        # Find max number
        query = """
        SELECT MAX(CAST(SUBSTRING(id_domanda FROM 2) AS INTEGER)) as max_number
        FROM qa_entries
        WHERE id_domanda IS NOT NULL
        AND id_domanda ~ '^N[0-9]+$'
        """
        
        result = await db.fetchrow(query)
        
        if result and result['max_number'] is not None:
            next_number = result['max_number'] + 1
            logger.info(f"   Next number: {next_number}")
        else:
            next_number = 1
            logger.info("   Starting from N0001")
        
        # Format with padding
        new_id_domanda = f"N{next_number:04d}"
        
        logger.info(f"✅ Generated id_domanda: {new_id_domanda}")
        return new_id_domanda
        
    except Exception as e:
        logger.error(f"❌ Error generating id_domanda: {e}")
        # Fallback: use timestamp
        fallback_number = int(time.time()) % 10000
        fallback_id = f"N{fallback_number:04d}"
        logger.warning(f"⚠️ Using fallback id_domanda: {fallback_id}")
        return fallback_id


# ==================== Q&A Endpoints ====================

@router.get("/region/{region}", response_model=List[QAItem])
async def get_qa_by_region(
    region: str,
    current_user: dict = Depends(get_current_user_from_token)
):
    """
    Get all Q&A entries for a specific region

    Args:
        region: Region name
        current_user: Authenticated user

    Returns:
        List of Q&A items
    """
    try:
        # Enforce region-based access control
        user_region = current_user.get('region', 'master')

        if user_region and user_region != "master":
            # Regional users can ONLY access their assigned region
            if region != user_region:
                raise HTTPException(
                    status_code=403,
                    detail=f"Non autorizzato ad accedere a questa regione. Sei un utente {user_region} e puoi accedere solo ai dati della regione {user_region}."
                )

        logger.info(f"📋 Getting Q&A for region: {region}")

        query = """
        SELECT qa_id, question, answer, region, pinecone_id,
               created_at, updated_at, created_by, updated_by, id_domanda
        FROM qa_entries
        WHERE region = $1
        ORDER BY updated_at DESC, created_at DESC
        """

        results = await db.fetch(query, region)

        qa_list = [QAItem(**row) for row in results]

        logger.info(f"✅ Found {len(qa_list)} Q&A entries for region {region}")
        return qa_list

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error fetching Q&A for region {region}: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Errore nel recupero delle Q&A: {str(e)}"
        )


@router.post("", response_model=QACreateResponse)
async def create_qa(
    qa_data: QACreate,
    current_user: dict = Depends(get_current_user_from_token)
):
    """
    Create new Q&A entry (PostgreSQL + Pinecone)
    
    Args:
        qa_data: Q&A creation data
        current_user: Authenticated user
    
    Returns:
        Creation response with IDs
    """
    try:
        user_name = current_user['name']
        user_region = current_user.get('region', 'master')

        logger.info(f"🆕 Creating new Q&A")
        logger.info(f"   Question: {qa_data.question[:50]}...")
        logger.info(f"   Region: {qa_data.region}")
        logger.info(f"   Created by: {user_name}")

        # Validate
        if not qa_data.question.strip():
            raise HTTPException(status_code=400, detail="La domanda non può essere vuota")

        if not qa_data.answer.strip():
            raise HTTPException(status_code=400, detail="La risposta non può essere vuota")

        if not qa_data.region.strip():
            raise HTTPException(status_code=400, detail="La regione non può essere vuota")

        # Enforce region-based access control for creation
        if user_region and user_region != "master":
            # Regional users can ONLY create Q&A for their assigned region
            if qa_data.region != user_region:
                raise HTTPException(
                    status_code=403,
                    detail=f"Non autorizzato a creare Q&A per questa regione. Sei un utente {user_region} e puoi creare solo Q&A per la regione {user_region}."
                )
        
        # Generate id_domanda
        new_id_domanda = await generate_next_id_domanda()
        
        # Get Italy time
        italy_time_naive = get_italy_time_naive()
        
        # Insert into PostgreSQL
        query = """
        INSERT INTO qa_entries
        (question, answer, region, created_by, updated_by, created_at, updated_at, id_domanda)
        VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
        RETURNING qa_id
        """
        
        qa_id = await db.fetchval(
            query,
            qa_data.question.strip(),
            qa_data.answer.strip(),
            qa_data.region.strip(),
            user_name,
            user_name,
            italy_time_naive,
            italy_time_naive,
            new_id_domanda
        )
        
        if not qa_id:
            raise HTTPException(
                status_code=500,
                detail="Errore durante l'inserimento in PostgreSQL"
            )
        
        logger.info(f"✅ PostgreSQL insert successful, ID: {qa_id}")
        
        # Save to Pinecone
        pinecone_id = await save_to_pinecone(
            qa_id,
            qa_data.question.strip(),
            qa_data.answer.strip(),
            qa_data.region.strip()
        )
        
        # Update PostgreSQL with pinecone_id
        update_query = "UPDATE qa_entries SET pinecone_id = $1 WHERE qa_id = $2"
        await db.execute(update_query, pinecone_id, qa_id)
        
        logger.info(f"✅ Pinecone ID updated in PostgreSQL: {pinecone_id}")
        
        return QACreateResponse(
            success=True,
            message="Q&A creata con successo in PostgreSQL e Pinecone",
            qa_id=qa_id,
            pinecone_id=pinecone_id,
            id_domanda=new_id_domanda,
            created_by=user_name,
            created_at=italy_time_naive.isoformat(),
            updated_at=italy_time_naive.isoformat()
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error creating Q&A: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=500,
            detail=f"Errore nella creazione della Q&A: {str(e)}"
        )


@router.get("/{qa_id}", response_model=QAItem)
async def get_qa_by_id(qa_id: int):
    """
    Get specific Q&A by ID
    
    Args:
        qa_id: Q&A ID
    
    Returns:
        Q&A item
    """
    try:
        logger.info(f"🔍 Getting Q&A by ID: {qa_id}")
        
        query = """
        SELECT qa_id, question, answer, region, pinecone_id,
               created_at, updated_at, created_by, updated_by, id_domanda
        FROM qa_entries
        WHERE qa_id = $1
        """
        
        result = await db.fetchrow(query, qa_id)
        
        if not result:
            logger.warning(f"❌ Q&A {qa_id} not found")
            raise HTTPException(status_code=404, detail="Q&A non trovata")
        
        logger.info(f"✅ Found Q&A {qa_id}")
        
        return QAItem(**result)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error fetching Q&A {qa_id}: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Errore nel recupero della Q&A: {str(e)}"
        )


@router.put("/{qa_id}", response_model=QAUpdateResponse)
async def update_qa(
    qa_id: int,
    qa_data: QAUpdate,
    current_user: dict = Depends(get_current_user_from_token)
):
    """
    Update Q&A (PostgreSQL + Pinecone)
    
    Args:
        qa_id: Q&A ID to update
        qa_data: Updated Q&A data
        current_user: Authenticated user
    
    Returns:
        Update response
    """
    try:
        user_name = current_user['name']
        
        logger.info(f"🔄 Updating Q&A {qa_id}")
        logger.info(f"   Updated by: {user_name}")
        
        # Validate
        if not qa_data.question.strip():
            raise HTTPException(status_code=400, detail="La domanda non può essere vuota")
        
        if not qa_data.answer.strip():
            raise HTTPException(status_code=400, detail="La risposta non può essere vuota")
        
        # Get existing Q&A
        existing_query = "SELECT qa_id, region, pinecone_id FROM qa_entries WHERE qa_id = $1"
        existing_qa = await db.fetchrow(existing_query, qa_id)
        
        if not existing_qa:
            logger.warning(f"❌ Q&A {qa_id} not found")
            raise HTTPException(status_code=404, detail="Q&A non trovata")
        
        # Get Italy time
        italy_time_naive = get_italy_time_naive()
        
        # Update PostgreSQL
        update_query = """
        UPDATE qa_entries
        SET question = $1, answer = $2, updated_by = $3, updated_at = $4
        WHERE qa_id = $5
        """
        
        await db.execute(
            update_query,
            qa_data.question.strip(),
            qa_data.answer.strip(),
            user_name,
            italy_time_naive,
            qa_id
        )
        
        logger.info(f"✅ PostgreSQL update successful")
        
        # Update Pinecone
        old_pinecone_id = existing_qa['pinecone_id']
        region = existing_qa['region']
        
        new_pinecone_id = await update_pinecone(
            old_pinecone_id,
            qa_data.question.strip(),
            qa_data.answer.strip(),
            region,
            qa_id
        )
        
        # Update pinecone_id in PostgreSQL
        update_pinecone_query = "UPDATE qa_entries SET pinecone_id = $1 WHERE qa_id = $2"
        await db.execute(update_pinecone_query, new_pinecone_id, qa_id)
        
        logger.info(f"✅ Pinecone update successful")
        
        return QAUpdateResponse(
            success=True,
            message="Q&A aggiornata con successo in PostgreSQL e Pinecone",
            qa_id=qa_id,
            old_pinecone_id=old_pinecone_id,
            new_pinecone_id=new_pinecone_id,
            updated_by=user_name,
            updated_at=italy_time_naive.isoformat()
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error updating Q&A {qa_id}: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=500,
            detail=f"Errore nell'aggiornamento della Q&A: {str(e)}"
        )


@router.delete("/{qa_id}", response_model=QADeleteResponse)
async def delete_qa(qa_id: int, current_user: dict = Depends(get_current_user_from_token)):
    """
    Delete Q&A (PostgreSQL + Pinecone)
    
    Args:
        qa_id: Q&A ID to delete
        current_user: Authenticated user
    
    Returns:
        Delete response
    """
    try:
        logger.info(f"🗑️ Deleting Q&A {qa_id}")
        
        # Get existing Q&A
        existing_query = "SELECT qa_id, pinecone_id FROM qa_entries WHERE qa_id = $1"
        existing_qa = await db.fetchrow(existing_query, qa_id)
        
        if not existing_qa:
            logger.warning(f"❌ Q&A {qa_id} not found")
            raise HTTPException(status_code=404, detail="Q&A non trovata")
        
        pinecone_id = existing_qa['pinecone_id']
        
        # Delete from Pinecone
        if pinecone_id:
            await delete_from_pinecone(pinecone_id)
        
        # Delete from PostgreSQL
        delete_query = "DELETE FROM qa_entries WHERE qa_id = $1"
        await db.execute(delete_query, qa_id)
        
        logger.info(f"✅ Q&A {qa_id} deleted successfully")
        
        return QADeleteResponse(
            success=True,
            message="Q&A eliminata con successo da PostgreSQL e Pinecone",
            qa_id=qa_id,
            pinecone_id=pinecone_id
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error deleting Q&A {qa_id}: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Errore nell'eliminazione della Q&A: {str(e)}"
        )


@router.get("/stats/{region}", response_model=QAStatsResponse)
async def get_qa_stats(region: str):
    """
    Get Q&A statistics for a region
    
    Args:
        region: Region name
    
    Returns:
        Q&A statistics
    """
    try:
        logger.info(f"📊 Getting Q&A stats for region: {region}")
        
        query = """
        SELECT
            COUNT(*) as total_qa,
            COUNT(CASE WHEN created_at >= NOW() - INTERVAL '27 days' THEN 1 END) as recent_qa,
            COUNT(CASE WHEN updated_at >= NOW() - INTERVAL '27 days' THEN 1 END) as updated_qa
        FROM qa_entries
        WHERE region = $1
        """
        
        result = await db.fetchrow(query, region)
        
        stats = QAStatsResponse(
            region=region,
            total_qa=result['total_qa'],
            recent_qa=result['recent_qa'],
            updated_qa=result['updated_qa']
        )
        
        logger.info(f"✅ Stats for {region}: {stats}")
        return stats
        
    except Exception as e:
        logger.error(f"❌ Error fetching Q&A stats for region {region}: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Errore nel recupero delle statistiche: {str(e)}"
        )
