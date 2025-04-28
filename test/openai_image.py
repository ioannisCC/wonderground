from openai import OpenAI
import base64
from dotenv import load_dotenv
load_dotenv()

client = OpenAI()

prompt = """
Inside a softly lit, traditional Japanese sushi bar, highly realistic humanoid fish chefs prepare elegant, surreal sushi. Their faces — fish-like with expressive eyes, textured scales, and ceremonial white uniforms — remain unchanged from the previous image.

The food they prepare is distinctly unsettling: nigiri and sashimi-style dishes built on hand-pressed rice, topped with organic, pale sculptural elements that bear an unmistakable resemblance to human features — slender finger-like forms, curved ear-like structures, small round shapes with subtle facial hints, and curled slices that echo muscle or fatty tissue. One piece resembles a delicate nose resting atop rice. Another has a curled segment resembling a scalp or temple.

The plating is refined: edible flowers, thin lines of soy glaze, pickled garnish, and fresh wasabi. One dish is a sashimi-style platter with multiple “soft tissue” pieces laid out artfully in rows, presented with reverence. A side bowl contains a ceviche-like dish with tiny anatomical sculptures suspended in broth with herbs and citrus.

Everything feels handcrafted, intentional, and quietly grotesque. The setting is pristine — clean wood counters, paper lanterns, hanging calligraphy. The scene is shot in ultra-real 8K DSLR quality, with cinematic golden lighting and shallow depth of field that keeps the viewer’s eye locked on the surreal sushi.

The message is immediate and clear: this is a reversed world, where humans are the delicacy — not through gore, but through culinary mastery and eerie symbolism.
"""

result = client.images.generate(
    model="gpt-image-1",
    size="1024x1024",
    quality="high",
    output_format="png",
    prompt=prompt,
    moderation="low",
)

image_base64 = result.data[0].b64_json
image_bytes = base64.b64decode(image_base64)

# save the image to a file
with open("otter.png", "wb") as f:
    f.write(image_bytes)