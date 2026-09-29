"""Create the first personal admin interactively, without passwords in arguments."""
import getpass
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from scouting.portal.accounts import bootstrap_admin

if __name__ == '__main__':
    username = input('Correo personal verificado: ')
    name = input('Nombre: ')
    password = getpass.getpass('Contraseña (mínimo 12 caracteres): ')
    if password != getpass.getpass('Repetir contraseña: '):
        raise SystemExit('Las contraseñas no coinciden.')
    bootstrap_admin(username, name, password)
    print('Administrador creado.')
