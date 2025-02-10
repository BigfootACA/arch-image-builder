from builder.disk.image import ImageBuilder


class ImageContentBuilder:
	builder: ImageBuilder
	properties: dict

	def __init__(self, builder: ImageBuilder):
		self.builder = builder
		self.properties = {}

	def build(self): pass

	def auto_create_image(self) -> bool:
		return True

	def build_post(self):
		pass


class ImageContentBuilders:
	types: list[tuple[str, type[ImageContentBuilder]]] = []

	@staticmethod
	def init():
		if len(ImageContentBuilders.types) > 0: return
		from builder.disk.types import types
		ImageContentBuilders.types.extend(types)

	@staticmethod
	def find_builder(name: str) -> type[ImageContentBuilder]:
		types = ImageContentBuilders.types
		return next((t[1] for t in types if name == t[0]), None)
