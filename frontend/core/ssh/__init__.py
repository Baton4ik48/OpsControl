from core.ssh.common import SSHRotateError, try_auth
from core.ssh.rotate_linux import rotate_linux_password
from core.ssh.rotate_cisco import rotate_cisco_password
from core.ssh.rotate_nateks import rotate_nateks_password

# Типы устройств с поддержкой автоматической смены пароля по SSH.
# "natex" — backward compat для старых записей в БД.
ROTATE_FN = {
    "linux": rotate_linux_password,
    "nateks": rotate_nateks_password,
    "natex": rotate_nateks_password,
    "cisco": rotate_cisco_password,
}
