from sqlalchemy import Column, ForeignKey, String, Integer, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
import sqlalchemy

from database import Base

class SearchQuery(Base):
  __tablename__ = 'search_query'
  id = Column(UUID, primary_key=True, nullable=False, server_default=func.gen_random_uuid())
  status_id = Column(Integer, ForeignKey('search_query_status.id'), nullable=False, default=0)

  query_string = Column(String, nullable=False)
  pages = Column(Integer, nullable=False, server_default='1')
  time_range = Column(String, nullable=False)
  language = Column(String, nullable=False)
  safe_search = Column(Integer, nullable=False)

  search_results = relationship("SearchResult", back_populates="search_query", lazy="selectin")
  status = relationship("SearchQueryStatus", back_populates="search_query", lazy="selectin")

class SearchQueryStatus(Base):
  __tablename__ = 'search_query_status'
  id = Column(Integer, primary_key=True, nullable=False)
  description = Column(String, nullable=False)
  search_query = relationship("SearchQuery", back_populates="status", lazy="selectin")

class SearchResult(Base):
  __tablename__ = 'search_result'
  id = Column(UUID, primary_key=True, nullable=False, server_default=func.gen_random_uuid())
  search_query_id = Column(UUID, ForeignKey('search_query.id', ondelete='CASCADE'), nullable=False)
  img_src = Column(String, nullable=False)
  thumb_src = Column(String)
  search_query = relationship("SearchQuery", back_populates="search_results", lazy="selectin")