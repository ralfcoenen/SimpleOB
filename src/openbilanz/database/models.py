from sqlalchemy import (
    Column,
    Integer,
    String,
    ForeignKey
)

from sqlalchemy.orm import relationship

from .database import Base



class Mandant(Base):

    __tablename__ = "mandanten"


    id = Column(
        Integer,
        primary_key=True
    )


    name = Column(
        String,
        nullable=False
    )


    rechtsform = Column(
        String
    )


    steuernummer = Column(
        String
    )


    finanzamt = Column(
        String
    )


    wirtschaftsjahre = relationship(
        "Wirtschaftsjahr",
        back_populates="mandant"
    )



class Wirtschaftsjahr(Base):

    __tablename__ = "wirtschaftsjahre"


    id = Column(
        Integer,
        primary_key=True
    )


    mandant_id = Column(
        Integer,
        ForeignKey(
            "mandanten.id"
        )
    )


    jahr = Column(
        Integer,
        nullable=False
    )


    mandant = relationship(
        "Mandant",
        back_populates="wirtschaftsjahre"
    )
    
