from sqlalchemy import Column, BigInteger, String, DateTime
from traces_api.database import Base


class ModelUnit(Base):

    __tablename__ = 'unit'

    id_unit = Column(BigInteger(), primary_key=True, autoincrement=True)
    creation_time = Column(DateTime, nullable=False)
    last_update_time = Column(DateTime, nullable=False)
    annotation = Column(String(255))
    ip_mac_mapping = Column(String(255))
    uploaded_file_location = Column(String(255), nullable=False)
    stage = Column(String(), nullable=False)

    def dict(self):
        return dict(
            id_unit=self.id_unit,
            creation_time=self.creation_time.timestamp(),
            last_update_time=self.last_update_time.timestamp(),
            stage=self.stage
        )
