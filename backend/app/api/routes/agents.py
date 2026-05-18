from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional

from app.core.database import get_db
from app.models import Agent, Collection

router = APIRouter(prefix="/agents", tags=["agents"])


class AgentResponse(BaseModel):
    id: str
    name: str
    specialty: str
    system_prompt: str
    collection_id: Optional[str]
    collection_name: Optional[str]
    provider: str
    model_name: str
    temperature: float
    is_active: bool
    created_at: str

    class Config:
        from_attributes = True


class AgentCreate(BaseModel):
    name: str
    specialty: str = ""
    system_prompt: str = ""
    collection_id: Optional[str] = None
    provider: str = "ollama"
    model_name: str = "llama3.2:3b"
    temperature: float = 0.3


class AgentUpdate(BaseModel):
    name: Optional[str] = None
    specialty: Optional[str] = None
    system_prompt: Optional[str] = None
    collection_id: Optional[str] = None
    provider: Optional[str] = None
    model_name: Optional[str] = None
    temperature: Optional[float] = None
    is_active: Optional[bool] = None


class AgentStats(BaseModel):
    total_queries: int = 0
    successful_queries: int = 0
    avg_response_time: float = 0.0


@router.get("", response_model=list[AgentResponse])
def list_agents(db: Session = Depends(get_db)):
    agents = db.query(Agent).order_by(Agent.created_at.desc()).all()
    result = []
    for agent in agents:
        collection_name = None
        if agent.collection_id:
            col = db.query(Collection).filter(Collection.id == agent.collection_id).first()
            collection_name = col.name if col else None
        result.append(AgentResponse(
            id=agent.id,
            name=agent.name,
            specialty=agent.specialty or "",
            system_prompt=agent.system_prompt or "",
            collection_id=agent.collection_id,
            collection_name=collection_name,
            provider=agent.provider or "ollama",
            model_name=agent.model_name,
            temperature=float(agent.temperature or 0.3),
            is_active=bool(agent.is_active),
            created_at=agent.created_at.isoformat() if agent.created_at else ""
        ))
    return result


@router.post("", response_model=AgentResponse)
def create_agent(agent_data: AgentCreate, db: Session = Depends(get_db)):
    if agent_data.collection_id:
        col = db.query(Collection).filter(Collection.id == agent_data.collection_id).first()
        if not col:
            raise HTTPException(status_code=400, detail="Collection nao encontrada")

    default_prompt = (
        f"Voce e um assistente especializado em {agent_data.specialty}. "
        f"Use apenas informacoes da sua base de conhecimento para responder. "
        f"Se a informacao nao estiver disponivel, diga claramente."
    )

    new_agent = Agent(
        name=agent_data.name,
        specialty=agent_data.specialty,
        system_prompt=agent_data.system_prompt or default_prompt,
        collection_id=agent_data.collection_id,
        provider=agent_data.provider,
        model_name=agent_data.model_name,
        temperature=str(agent_data.temperature),
        is_active=1
    )
    db.add(new_agent)
    db.commit()
    db.refresh(new_agent)

    collection_name = None
    if new_agent.collection_id:
        col = db.query(Collection).filter(Collection.id == new_agent.collection_id).first()
        collection_name = col.name if col else None

    return AgentResponse(
        id=new_agent.id,
        name=new_agent.name,
        specialty=new_agent.specialty or "",
        system_prompt=new_agent.system_prompt or "",
        collection_id=new_agent.collection_id,
        collection_name=collection_name,
        provider=new_agent.provider or "ollama",
        model_name=new_agent.model_name,
        temperature=float(new_agent.temperature or 0.3),
        is_active=bool(new_agent.is_active),
        created_at=new_agent.created_at.isoformat() if new_agent.created_at else ""
    )


@router.get("/{agent_id}", response_model=AgentResponse)
def get_agent(agent_id: str, db: Session = Depends(get_db)):
    agent = db.query(Agent).filter(Agent.id == agent_id).first()
    if not agent:
        raise HTTPException(status_code=404, detail="Agente nao encontrado")

    collection_name = None
    if agent.collection_id:
        col = db.query(Collection).filter(Collection.id == agent.collection_id).first()
        collection_name = col.name if col else None

    return AgentResponse(
        id=agent.id,
        name=agent.name,
        specialty=agent.specialty or "",
        system_prompt=agent.system_prompt or "",
        collection_id=agent.collection_id,
        collection_name=collection_name,
        provider=agent.provider or "ollama",
        model_name=agent.model_name,
        temperature=float(agent.temperature or 0.3),
        is_active=bool(agent.is_active),
        created_at=agent.created_at.isoformat() if agent.created_at else ""
    )


@router.put("/{agent_id}", response_model=AgentResponse)
def update_agent(agent_id: str, update: AgentUpdate, db: Session = Depends(get_db)):
    agent = db.query(Agent).filter(Agent.id == agent_id).first()
    if not agent:
        raise HTTPException(status_code=404, detail="Agente nao encontrado")

    if update.name is not None:
        agent.name = update.name
    if update.specialty is not None:
        agent.specialty = update.specialty
    if update.system_prompt is not None:
        agent.system_prompt = update.system_prompt
    if update.collection_id is not None:
        col = db.query(Collection).filter(Collection.id == update.collection_id).first()
        if not col:
            raise HTTPException(status_code=400, detail="Collection nao encontrada")
        agent.collection_id = update.collection_id
    if update.provider is not None:
        agent.provider = update.provider
    if update.model_name is not None:
        agent.model_name = update.model_name
    if update.temperature is not None:
        agent.temperature = str(update.temperature)
    if update.is_active is not None:
        agent.is_active = 1 if update.is_active else 0

    db.commit()
    db.refresh(agent)

    collection_name = None
    if agent.collection_id:
        col = db.query(Collection).filter(Collection.id == agent.collection_id).first()
        collection_name = col.name if col else None

    return AgentResponse(
        id=agent.id,
        name=agent.name,
        specialty=agent.specialty or "",
        system_prompt=agent.system_prompt or "",
        collection_id=agent.collection_id,
        collection_name=collection_name,
        provider=agent.provider or "ollama",
        model_name=agent.model_name,
        temperature=float(agent.temperature or 0.3),
        is_active=bool(agent.is_active),
        created_at=agent.created_at.isoformat() if agent.created_at else ""
    )


@router.delete("/{agent_id}")
def delete_agent(agent_id: str, db: Session = Depends(get_db)):
    agent = db.query(Agent).filter(Agent.id == agent_id).first()
    if not agent:
        raise HTTPException(status_code=404, detail="Agente nao encontrado")
    db.delete(agent)
    db.commit()
    return {"message": "Agente excluido"}


@router.put("/{agent_id}/collection/{collection_id}")
def assign_collection(agent_id: str, collection_id: str, db: Session = Depends(get_db)):
    agent = db.query(Agent).filter(Agent.id == agent_id).first()
    if not agent:
        raise HTTPException(status_code=404, detail="Agente nao encontrado")
    col = db.query(Collection).filter(Collection.id == collection_id).first()
    if not col:
        raise HTTPException(status_code=404, detail="Collection nao encontrada")

    agent.collection_id = collection_id
    db.commit()

    return {"message": f"Collection {col.name} associada ao agente {agent.name}"}


@router.get("/{agent_id}/stats", response_model=AgentStats)
def get_agent_stats(agent_id: str, db: Session = Depends(get_db)):
    agent = db.query(Agent).filter(Agent.id == agent_id).first()
    if not agent:
        raise HTTPException(status_code=404, detail="Agente nao encontrado")

    return AgentStats(
        total_queries=0,
        successful_queries=0,
        avg_response_time=0.0
    )