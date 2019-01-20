import json
from enum import Enum
from datetime import datetime
from threading import Thread
from sqlalchemy import desc, update, and_, or_

from traces_api.database.model.mix import ModelMix, ModelMixLabel, ModelMixOrigin, ModelMixFileGeneration

from traces_api.modules.annotated_unit.service import AnnotatedUnitService
from traces_api.tools import TraceNormalizer, TraceMixing
from traces_api.storage import FileStorage, File
from traces_api.modules.dataset.service import Mapping


class AnnotatedUnitDoesntExistsException(Exception):
    """
    Annotated unit doesnt exits
    This exception is raised when annotated unit is not found in database
    """
    pass


class MixDoesntExistsException(Exception):
    """
    mix doesnt exits
    This exception is raised when mix is not found in database
    """
    pass


class OperatorEnum(Enum):
    """
    SQL operators
    """
    AND = "AND"
    OR = "OR"


class MixService:
    """
    This class allows to perform all business logic regarding to mixes
    """

    def __init__(self, session_maker, annotated_unit_service: AnnotatedUnitService, file_storage: FileStorage, trace_normalizer: TraceNormalizer, trace_mixing: TraceMixing):
        self._session_maker = session_maker
        self._annotated_unit_service = annotated_unit_service
        self._file_storage = file_storage
        self._trace_normalizer = trace_normalizer
        self._trace_mixing = trace_mixing

    @property
    def _session(self):
        return self._session_maker()

    def _exits_ann_unit(self, id_annotated_unit):
        """
        This methods checks if annotated unit exists in database
        :param id_annotated_unit:
        :return: True if exists otherwise False
        """
        return self._annotated_unit_service.get_annotated_unit(id_annotated_unit) is not None

    def _mix(self, mix_generation_id, annotated_units_data):
        if not (all([self._exits_ann_unit(ann_unit["id_annotated_unit"]) for ann_unit in annotated_units_data])):
            raise AnnotatedUnitDoesntExistsException()

        self._update_mix_generation_progress(mix_generation_id, 1)
        mixing = self._trace_mixing.create_new_mixer(File.create_new().location)

        for ann_unit in annotated_units_data:
            id_annotated_unit = ann_unit["id_annotated_unit"]

            new_ann_unit_file = File.create_new()
            ann_unit_file = self._annotated_unit_service.download_annotated_unit(id_annotated_unit)
            configuration = self._trace_normalizer.prepare_configuration(ann_unit["ip_mapping"], ann_unit["mac_mapping"], ann_unit["timestamp"])
            self._trace_normalizer.normalize(ann_unit_file.location, new_ann_unit_file.location, configuration)

            mixing.mix(new_ann_unit_file.location)

        self._update_mix_generation_progress(mix_generation_id, 99)

        mix_file = File(mixing.get_mixed_file_location())
        with open(mix_file.location, "rb") as f:
            file_name = self._file_storage.save_file(f)

        mix_generation = self.get_mix_generation_by_id_generation(mix_generation_id)
        mix_generation.progress = 100
        mix_generation.file_location = file_name

        self._session.add(mix_generation)
        self._session.commit()

    def create_mix(self, name, description, labels, annotated_units):
        """
        Create mix based on annotated_units

        :param name: mix name
        :param description: mix description
        :param labels: labels that will be connected to mix
        :param annotated_units: annotated units data used for mix generation
        :return: Modelmix newly created mix
        """
        if not (all([self._exits_ann_unit(ann_unit["id_annotated_unit"]) for ann_unit in annotated_units])):
            raise AnnotatedUnitDoesntExistsException()

        mix = ModelMix(
            name=name,
            description=description,
            creation_time=datetime.now(),
            labels=[ModelMixLabel(label=l) for l in labels],
            origins=[
                ModelMixOrigin(
                    id_annotated_unit=ann_unit["id_annotated_unit"],
                    ip_mapping=json.dumps(ann_unit["ip_mapping"]),
                    mac_mapping=json.dumps(ann_unit["mac_mapping"]),
                    timestamp=ann_unit["timestamp"],
                ) for ann_unit in annotated_units
            ],
        )

        self._session.add(mix)
        self._session.commit()
        return mix

    def generate_mix(self, id_mix):
        """
        Generate mix file

        :param id_mix: id of existing mix
        :return: ModelMixFileGeneration
        """

        mix = self.get_mix(id_mix)
        if not mix:
            raise MixDoesntExistsException(id_mix)

        annotated_units_data = []
        for origin in mix.origins:
            annotated_units_data.append(dict(
                id_annotated_unit=origin.id_annotated_unit,
                ip_mapping=Mapping.create_from_dict(json.loads(origin.ip_mapping)),
                mac_mapping=Mapping.create_from_dict(json.loads(origin.mac_mapping)),
                timestamp=origin.timestamp,
            ))

        mix_generation = ModelMixFileGeneration(
            id_mix=mix.id_mix,
            creation_time=datetime.now(),
            expired=False,
            progress=0,
        )
        self._session.add(mix_generation)
        self._session.commit()

        thread = Thread(target=self._mix, args=(mix_generation.id_mix_generation, annotated_units_data))
        thread.start()

        return mix_generation

    def get_mix(self, id_mix):
        """
        Get mix by id_mix from database

        :param id_mix:
        :return: mix
        """
        mix = self._session.query(ModelMix).filter(ModelMix.id_mix == id_mix).first()
        if not mix:
            raise MixDoesntExistsException()
        return mix

    def get_mix_generation(self, id_mix):
        """
        Find mix file generation by mix_id
        :param id_mix:
        :return: ModelMixFileGeneration
        """
        q = self._session.query(ModelMixFileGeneration).filter_by(expired=False).filter_by(id_mix=id_mix)
        q = q.order_by(desc(ModelMixFileGeneration.creation_time))
        mix_generation = q.first()
        return mix_generation

    def get_mix_generation_by_id_generation(self, id_mix_generation):
        """
        Find mix generation by id_mix_generation
        :param id_mix_generation:
        :return: ModelMixFileGeneration
        """
        q = self._session.query(ModelMixFileGeneration).filter_by(id_mix_generation=id_mix_generation)
        mix_generation = q.first()
        return mix_generation

    def _update_mix_generation_progress(self, id_mix_generation, progress):
        """
        Update progress of mix file generation in database
        :param id_mix_generation:
        :param progress: progress in percent - (0 - 100)
        """
        q = update(ModelMixFileGeneration).values(progress=progress)\
            .where(ModelMixFileGeneration.id_mix_generation == id_mix_generation)
        self._session.execute(q)
        self._session.commit()

    def download_mix(self, id_mix):
        """
        Return absolute file location of mix

        :param id_mix:
        :return: mix File
        """
        mix_generation = self.get_mix_generation(id_mix)
        if not mix_generation:
            raise MixDoesntExistsException()
        return self._file_storage.get_file(mix_generation.file_location)

    def get_mixes(self, limit=100, page=0, name=None, labels=None, description=None, operator=OperatorEnum.AND):
        """
        Find mixes

        :param limit: number of mixes returned in one request, default 100
        :param page: page id, starting from 0
        :param name: search mix by name - exact match
        :param labels: search mix by labels
        :param description: search mix by description
        :param operator: OperatorEnum
        :return: list of mixes that match given criteria
        """
        q = self._session.query(ModelMix)

        filters = []

        if name:
            filters.append(ModelMix.name.like("%{}%".format(name)))

        if description:
            filters.append(ModelMix.description.like("%{}%".format(description)))

        if labels:
            for label in labels:
                sub_q = self._session.query(ModelMix).filter(ModelMixLabel.label == label).filter(
                    ModelMixLabel.id_mix == ModelMix.id_mix
                )
                filters.append(sub_q.exists())

        if operator is OperatorEnum.AND:
            q = q.filter(and_(*filters))
        else:
            q = q.filter(or_(*filters))

        q = q.order_by(desc(ModelMix.creation_time))
        q = q.offset(page*limit).limit(limit)

        ann_units = q.all()
        return ann_units

    def delete_mix(self, id_mix):
        """
        Delete mix using id

        :param id_mix: ID to be deleted
        """

        mix = self.get_mix(id_mix)
        if not mix:
            raise MixDoesntExistsException()

        self._session.delete(mix)
        self._session.commit()
