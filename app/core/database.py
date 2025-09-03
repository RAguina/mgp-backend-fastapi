# backend/app/core/database.py
"""
Database configuration for RAG system
Using SQLAlchemy with SQLite for development
"""

import os
import logging
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import StaticPool
from contextlib import contextmanager

from app.db.models import Base

logger = logging.getLogger(__name__)

# Database configuration
DATABASE_DIR = "data"
DATABASE_FILE = "rag_database.db"
DATABASE_PATH = os.path.join(DATABASE_DIR, DATABASE_FILE)
DATABASE_URL = f"sqlite:///{DATABASE_PATH}"

# Create data directory if it doesn't exist
os.makedirs(DATABASE_DIR, exist_ok=True)

# SQLAlchemy engine configuration
engine = create_engine(
    DATABASE_URL,
    echo=False,  # Set to True for SQL debugging
    connect_args={
        "check_same_thread": False,  # Needed for SQLite
    },
    poolclass=StaticPool,
)

# Session configuration
SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine
)


def create_tables():
    """
    Create all database tables
    """
    try:
        Base.metadata.create_all(bind=engine)
        logger.info("Database tables created successfully")
    except Exception as e:
        logger.error(f"Error creating database tables: {str(e)}")
        raise


def get_db() -> Session:
    """
    Dependency to get database session
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@contextmanager
def get_db_session():
    """
    Context manager for database sessions
    """
    db = SessionLocal()
    try:
        yield db
        db.commit()
    except Exception as e:
        db.rollback()
        logger.error(f"Database error: {str(e)}")
        raise
    finally:
        db.close()


def init_database():
    """
    Initialize database with tables and default data
    """
    try:
        logger.info("Initializing database...")
        
        # Create tables
        create_tables()
        
        # Add default configurations if needed
        with get_db_session() as db:
            from app.db.models import RAGConfiguration
            
            # Check if we have default configurations
            existing_configs = db.query(RAGConfiguration).count()
            
            if existing_configs == 0:
                logger.info("Adding default RAG configurations...")
                
                # Default embedding models
                default_embeddings = [
                    RAGConfiguration(
                        config_type="embedding_model",
                        name="bge-m3",
                        provider="huggingface",
                        config_data={
                            "model_path": "BAAI/bge-m3",
                            "dimensions": 1024,
                            "max_tokens": 8192,
                            "batch_size": 32
                        },
                        is_active=True,
                        is_default=True
                    ),
                    RAGConfiguration(
                        config_type="embedding_model",
                        name="e5-large",
                        provider="huggingface",
                        config_data={
                            "model_path": "intfloat/e5-large-v2",
                            "dimensions": 1024,
                            "max_tokens": 512,
                            "batch_size": 16
                        },
                        is_active=True,
                        is_default=False
                    )
                ]
                
                # Default vector stores
                default_vector_stores = [
                    RAGConfiguration(
                        config_type="vector_store",
                        name="milvus",
                        provider="milvus",
                        config_data={
                            "host": "localhost",
                            "port": 19530,
                            "collection_prefix": "rag_",
                            "index_type": "IVF_FLAT",
                            "metric_type": "L2"
                        },
                        is_active=True,
                        is_default=True
                    ),
                    RAGConfiguration(
                        config_type="vector_store",
                        name="weaviate",
                        provider="weaviate",
                        config_data={
                            "url": "http://localhost:8080",
                            "class_prefix": "RAG_",
                            "vectorizer": "none"
                        },
                        is_active=False,
                        is_default=False
                    )
                ]
                
                # Add to database
                for config in default_embeddings + default_vector_stores:
                    db.add(config)
                
                db.commit()
                logger.info("Default configurations added successfully")
        
        logger.info("Database initialized successfully")
        
    except Exception as e:
        logger.error(f"Error initializing database: {str(e)}")
        raise


def reset_database():
    """
    Reset database (drop and recreate all tables)
    WARNING: This will delete all data!
    """
    try:
        logger.warning("Resetting database - ALL DATA WILL BE LOST!")
        
        # Drop all tables
        Base.metadata.drop_all(bind=engine)
        
        # Recreate tables
        create_tables()
        
        # Reinitialize with default data
        init_database()
        
        logger.info("Database reset completed")
        
    except Exception as e:
        logger.error(f"Error resetting database: {str(e)}")
        raise


def check_database_health() -> dict:
    """
    Check database health and return status
    """
    try:
        with get_db_session() as db:
            # Try a simple query
            from app.db.models import RAGWorkspace
            count = db.query(RAGWorkspace).count()
            
            return {
                "status": "healthy",
                "database_url": DATABASE_URL,
                "tables_exist": True,
                "workspace_count": count,
                "connection": "ok"
            }
            
    except Exception as e:
        return {
            "status": "error",
            "database_url": DATABASE_URL,
            "error": str(e),
            "connection": "failed"
        }