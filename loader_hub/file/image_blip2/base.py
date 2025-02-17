from pathlib import Path
from typing import Dict, Optional, List

from llama_index.readers.base import BaseReader
from llama_index.readers.schema.base import Document, ImageDocument


class ImageVisionLLMReader(BaseReader):
    """Image parser.

    Caption image using Blip2 (a multimodal VisionLLM similar to GPT4).

    """

    def __init__(
        self,
        parser_config: Optional[Dict] = None,
        keep_image: bool = False,
        prompt: str = "Question: describe what you see in this image. Answer:",
    ):
        """Init params."""
        if parser_config is None:
            try:
                import torch  # noqa: F401
            except ImportError:
                raise ImportError(
                    "install pytorch to use the model: " "`pip install torch`"
                )
            try:
                from transformers import Blip2Processor, Blip2ForConditionalGeneration
            except ImportError:
                raise ImportError(
                    "transformers is required for using BLIP2 model: "
                    "`pip install transformers`"
                )
            try:
                import sentencepiece  # noqa: F401
            except ImportError:
                raise ImportError(
                    "sentencepiece is required for using BLIP2 model: "
                    "`pip install sentencepiece`"
                )
            try:
                from PIL import Image  # noqa: F401
            except ImportError:
                raise ImportError(
                    "PIL is required to read image files: " "`pip install Pillow`"
                )
            device = "cuda" if torch.cuda.is_available() else "cpu"
            dtype = torch.float16 if torch.cuda.is_available() else torch.float32
            processor = Blip2Processor.from_pretrained("Salesforce/blip2-opt-2.7b")
            model = Blip2ForConditionalGeneration.from_pretrained(
                "Salesforce/blip2-opt-2.7b", torch_dtype=dtype
            )
            parser_config = {"processor": processor, "model": model, "device": device, "dtype": dtype}
        self._parser_config = parser_config
        self._keep_image = keep_image
        self._prompt = prompt

    def load_data(self, file: Path, extra_info: Optional[Dict] = None) -> List[Document]:
        """Parse file."""
        from PIL import Image

        from gpt_index.img_utils import img_2_b64

        # load document image
        image = Image.open(file)
        if image.mode != "RGB":
            image = image.convert("RGB")

        # Encode image into base64 string and keep in document
        image_str: Optional[str] = None
        if self._keep_image:
            image_str = img_2_b64(image)

        # Parse image into text
        model = self.parser_config["model"]
        processor = self.parser_config["processor"]

        device = self.parser_config["device"]
        dtype = self.parser_config["dtype"]
        model.to(device)

        # unconditional image captioning
        
        inputs = processor(image, self._prompt, return_tensors="pt").to(device, dtype)

        out = model.generate(**inputs)
        text_str = processor.decode(out[0], skip_special_tokens=True)

        return ImageDocument(
            text=text_str,
            image=image_str,
        )
