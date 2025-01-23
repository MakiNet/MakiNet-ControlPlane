from pathlib import Path
from typing import Annotated, Optional

import uvicorn
from loguru import logger
from typer import Option, Typer

from . import utils
from .builder import build_image_from_directory, load_image, save_image
from .server import api

app = Typer(name="MakiNet Control Plane", help="Control Plane for MakiNet")
image_typer = Typer(name="image", help="Image related commands")

app.add_typer(image_typer)


@image_typer.command("build")
def build_image(
    source_path: Annotated[
        Path, Option("--source", "--src", "-s", help="Path to build")
    ] = Path.cwd(),
    output_path: Annotated[
        Optional[Path], Option("--output", "--out", "-o", help="Path to output")
    ] = None,
    compression: Annotated[
        bool, Option("--compression", "-c", help="Enable compression")
    ] = False,
):
    image = build_image_from_directory(source_path)

    if output_path is None:
        output_path = Path(f"./{image.slug}.{image.version}.image.zip")

    save_image(image, output_path, compression)

    logger.success(f"Build image {image.slug} version {image.version} success")
    logger.success(f"Image Info: {repr(image)}")
    logger.success(f"File Path: {output_path.absolute().as_posix()}")


@image_typer.command("load")
def load(
    image_path: Annotated[
        Path, Option("--image", "--img", "-i", help="Path to image")
    ] = Path.cwd()
    / "image.zip",
    extract_to: Annotated[
        Optional[Path], Option("--extract-to", "-o", help="Path to extract to")
    ] = None,
):
    image = load_image(image_path)

    logger.success(f"Load image {image_path} success")
    logger.info(f"Image Info: {repr(image)}")

    if extract_to is not None:
        if not extract_to.exists():
            extract_to.mkdir(parents=True, exist_ok=True)
            logger.info(f"Missing directory {extract_to}, creating...")

        if not extract_to.is_dir():
            logger.error(f"Extract to {extract_to} is not a directory")
            return

        logger.info("Starting extract image...")

        image.extract_to_directory(extract_to)


@app.command("server")
def server(
    debug: Annotated[bool, Option("--debug", "-v", help="Enable debug mode")] = False,
    host: Annotated[str, Option("--host", "-h", help="Host to bind to")] = "0.0.0.0",
    port: Annotated[int, Option("--port", "-p", help="Port to bind to")] = 10513,
    cert_file_dir: Annotated[
        Path, Option("--certs", help="Path to certificates")
    ] = utils.DEFAULT_CERT_FILE_DIR,
):
    api.debug = debug

    keyfile, certfile = utils.check_certs(cert_file_dir)

    uvicorn.run(
        api,
        host=host,
        port=port,
        ssl_keyfile=keyfile,
        ssl_certfile=certfile,
    )


if __name__ == "__main__":
    app()
