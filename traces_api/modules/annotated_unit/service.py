import json
from datetime import datetime

from traces_api.database.model.annotated_unit import ModelAnnotatedUnit, ModelAnnotatedUnitLabel

from traces_api.tools import TraceAnalyzer, TraceNormalizer
from traces_api.storage import FileStorage, File


class AnnotatedUnitService:
    """
    This class allows to perform all business logic regarding to annotated units
    """

    def __init__(self, session, file_storage: FileStorage, trace_analyzer: TraceAnalyzer, trace_normalizer: TraceNormalizer):
        self._session = session
        self._file_storage = file_storage
        self._trace_analyzer = trace_analyzer
        self._trace_normalizer = trace_normalizer

    def create_annotated_unit(self, name, description, ip_mapping, mac_mapping, timestamp, ip_details, unit_file_location, labels):
        """
        New annotated unit will be crated, normalized and saved into database

        :param name: Name of annotated unit
        :param description: Description of annotated unit
        :param ip_mapping:
        :param mac_mapping:
        :param timestamp:
        :param ip_details:
        :param unit_file_location:
        :param labels: Annotated unit labels
        :return:
        """
        random_file_name = "/tmp/TMP_TEST_FILE_NAME"
        with open(random_file_name, "w"):
            pass

        configuration = self._trace_normalizer.prepare_configuration(ip_mapping, mac_mapping, timestamp)
        self._trace_normalizer.normalize(unit_file_location, random_file_name, configuration)

        new = File(random_file_name)
        file_location = self._file_storage.save_file2(new)

        analyzed_data = self._trace_analyzer.analyze(new.location)

        annotated_unit = ModelAnnotatedUnit(
            name=name,
            description=description,
            creation_time=datetime.now(),
            stats=json.dumps(analyzed_data),
            ip_details=json.dumps(ip_details.dict()),
            file_location=file_location,
            labels=[ModelAnnotatedUnitLabel(label=l) for l in labels]
        )

        self._session.add(annotated_unit)
        return annotated_unit

    def get_annotated_unit(self, id_annotated_unit):
        """
        Get annotated unit by uid_id from database

        :param id_annotated_unit:
        :return: annotated unit
        """
        ann_unit = self._session.query(ModelAnnotatedUnit).filter(ModelAnnotatedUnit.id_annotated_unit == id_annotated_unit).first()
        return ann_unit

    def download_annotated_unit(self, id_annotated_unit):
        """
        Return absolute file location of annotated unit

        :param id_annotated_unit:
        :return: absolute path
        """
        ann_unit = self.get_annotated_unit(id_annotated_unit)

        return self._file_storage.get_absolute_file_path(ann_unit.file_location)

    def get_annotated_units(self):
        """
        Get all annotated units

        :return: list of annotated units
        """
        ann_units = self._session.query(ModelAnnotatedUnit).all()
        return ann_units
