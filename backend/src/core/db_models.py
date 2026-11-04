"""모든 모델을 한 번에 불러와 Base.metadata에 등록 (Alembic·테스트용).

새 모듈에 models.py를 만들면 여기에 한 줄 추가 (A·B 공동 파일).
"""

from modules.auth import models as auth_models  # noqa: F401
from modules.consent import models as consent_models  # noqa: F401
from modules.patient import models as patient_models  # noqa: F401
