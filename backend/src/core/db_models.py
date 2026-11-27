"""모든 모델을 한 번에 불러와 Base.metadata에 등록 (Alembic·테스트용).

새 모듈에 models.py를 만들면 여기에 한 줄 추가 (A·B 공동 파일).
"""

from modules.aftercare import models as aftercare_models  # noqa: F401
from modules.audit import models as audit_models  # noqa: F401
from modules.auth import models as auth_models  # noqa: F401
from modules.booking import models as booking_models  # noqa: F401
from modules.chatbot import models as chatbot_models  # noqa: F401
from modules.consent import models as consent_models  # noqa: F401
from modules.fx import models as fx_models  # noqa: F401
from modules.hospital import models as hospital_models  # noqa: F401
from modules.notification import models as notification_models  # noqa: F401
from modules.pageview import models as pageview_models  # noqa: F401
from modules.patient import models as patient_models  # noqa: F401
from modules.question import models as question_models  # noqa: F401
from modules.tenant import models as tenant_models  # noqa: F401
