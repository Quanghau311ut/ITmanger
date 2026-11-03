from collections.abc import Sequence

from modules.software_license.models import SoftwareLicense


class SoftwareLicenseView:
    @staticmethod
    def render_licenses(licenses: Sequence[SoftwareLicense]) -> str:
        if not licenses:
            return "Chưa có license phần mềm."
        return "\n".join(
            f"{item.software_name} | {item.license_type.value} | "
            f"{len(item.assigned_to)}/{item.quantity} | {item.expires_on or 'Vĩnh viễn'}"
            for item in licenses
        )
