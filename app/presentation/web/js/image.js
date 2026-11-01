// Reduz a foto no próprio celular antes de enviar: foto de câmera tem vários MB,
// aqui ela vira um JPEG de poucas centenas de KB.

const MAX_SIDE = 1280; // maior lado, em pixels
const MIN_SIDE = 480;
const MAX_BYTES = 350_000; // abaixo do limite do servidor (400 KB)
const QUALITIES = [0.8, 0.65, 0.5];

export async function compressImage(file) {
  if (!file?.type?.startsWith("image/")) throw new Error("Escolha um arquivo de imagem.");
  const source = await loadImage(file);
  try {
    let side = MAX_SIDE;
    for (;;) {
      const canvas = draw(source, side);
      for (const quality of QUALITIES) {
        const blob = await toBlob(canvas, quality);
        if (blob && blob.size <= MAX_BYTES) return blob;
      }
      if (side <= MIN_SIDE) break;
      side = Math.max(MIN_SIDE, Math.round(side * 0.75));
    }
  } finally {
    source.release();
  }
  throw new Error("Não foi possível reduzir esta imagem o suficiente. Tente outra foto.");
}

function draw(source, side) {
  const scale = Math.min(1, side / Math.max(source.width, source.height));
  const canvas = document.createElement("canvas");
  canvas.width = Math.max(1, Math.round(source.width * scale));
  canvas.height = Math.max(1, Math.round(source.height * scale));
  const context = canvas.getContext("2d");
  context.fillStyle = "#fff"; // PNG com transparência não vira fundo preto no JPEG
  context.fillRect(0, 0, canvas.width, canvas.height);
  context.drawImage(source.image, 0, 0, canvas.width, canvas.height);
  return canvas;
}

function toBlob(canvas, quality) {
  return new Promise((resolve) => canvas.toBlob(resolve, "image/jpeg", quality));
}

/** Decodifica respeitando a rotação da foto (EXIF), com plano B para navegadores antigos. */
async function loadImage(file) {
  try {
    const bitmap = await createImageBitmap(file, { imageOrientation: "from-image" });
    return { image: bitmap, width: bitmap.width, height: bitmap.height, release: () => bitmap.close?.() };
  } catch {
    const url = URL.createObjectURL(file);
    try {
      const image = new Image();
      image.src = url;
      await image.decode();
      return { image, width: image.naturalWidth, height: image.naturalHeight, release: () => URL.revokeObjectURL(url) };
    } catch {
      URL.revokeObjectURL(url);
      throw new Error("Não foi possível ler esta imagem.");
    }
  }
}
