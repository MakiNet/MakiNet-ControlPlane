from pathlib import Path
from socket import gethostname

from loguru import logger
from OpenSSL import crypto

DEFAULT_CERT_FILE_DIR = Path.home().joinpath(".local/share/makinet/certs")
_BACKGROUND_TASKS = []


def generate_self_signed_certs(
    cert_file_dir: Path = DEFAULT_CERT_FILE_DIR,
):
    cert_file_dir.mkdir(parents=True, exist_ok=True)

    logger.debug("Start to generate certs")

    # 创建密钥
    key = crypto.PKey()
    key.generate_key(crypto.TYPE_RSA, 2048)

    # 创建证书
    cert = crypto.X509()
    cert.get_subject().C = "IT"
    cert.get_subject().ST = "Makinet"
    cert.get_subject().L = "Makinet"
    cert.get_subject().O = "Makinet"
    cert.get_subject().OU = "Makinet"
    cert.get_subject().CN = gethostname()
    cert.set_serial_number(1000)
    cert.gmtime_adj_notBefore(0)
    cert.gmtime_adj_notAfter(10 * 365 * 24 * 60 * 60)
    cert.set_issuer(cert.get_subject())
    cert.set_pubkey(key)
    cert.sign(key, "sha256")

    cert_file_dir.joinpath("server.key").write_bytes(
        crypto.dump_privatekey(crypto.FILETYPE_PEM, key)
    )
    cert_file_dir.joinpath("server.crt").write_bytes(
        crypto.dump_certificate(crypto.FILETYPE_PEM, cert)
    )

    logger.debug("Generate certs success")


def check_certs(
    cert_file_dir: Path = DEFAULT_CERT_FILE_DIR,
):
    """检查证书，如果不存在则生成新的。

    Args:
        cert_file_dir (Path, optional): 证书文件夹. Defaults to DEFAULT_CERT_FILE_DIR.

    Returns:
        tuple[Path, Path]: 密钥文件和证书文件的路径，第一个是密钥文件，第二个是证书文件
    """
    cert_file_dir.mkdir(parents=True, exist_ok=True)

    key_file = cert_file_dir.joinpath("server.key")
    cert_file = cert_file_dir.joinpath("server.crt")

    if not key_file.exists() or not cert_file.exists():
        logger.warning("No certs found, generating new ones")
        logger.warning(
            "Self-signed certificates are not be trusted by your browser and os, we recommend you to use your own certificates issued by a trusted CA instead"
        )

        # 删除旧证书
        key_file.unlink(missing_ok=True)
        cert_file.unlink(missing_ok=True)

        # 生成新的
        generate_self_signed_certs(cert_file_dir)

    return (key_file, cert_file)
