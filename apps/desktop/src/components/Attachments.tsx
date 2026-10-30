import { FileText, Image as ImageIcon, X } from "lucide-react";

export type Attachment = { id: string; name: string; kind: "image" | "document"; chars: number; notice?: string };
const IMAGE = /\.(png|jpe?g|webp|gif|bmp)$/i;

// Images go to the model as JPEG of at most 1344 px: enough to read a screenshot, cheap in context.
async function toJpeg(blob: Blob): Promise<Uint8Array> {
  const bitmap = await createImageBitmap(blob);
  const scale = Math.min(1, 1344 / Math.max(bitmap.width, bitmap.height));
  const canvas = new OffscreenCanvas(Math.max(1, Math.round(bitmap.width * scale)), Math.max(1, Math.round(bitmap.height * scale)));
  const context = canvas.getContext("2d")!;
  context.fillStyle = "#fff";
  context.fillRect(0, 0, canvas.width, canvas.height);
  context.drawImage(bitmap, 0, 0, canvas.width, canvas.height);
  bitmap.close();
  return new Uint8Array(await (await canvas.convertToBlob({ type: "image/jpeg", quality: 0.85 })).arrayBuffer());
}

export async function upload(name: string, blob: Blob): Promise<Attachment> {
  if (IMAGE.test(name) || blob.type.startsWith("image/"))
    return window.alt.attach(name.replace(/\.[^.]*$/, "") + ".jpg", await toJpeg(blob));
  return window.alt.attach(name, new Uint8Array(await blob.arrayBuffer()));
}

export function AttachmentChips({ items, onRemove }: { items: Attachment[]; onRemove: (id: string) => void }) {
  if (!items.length) return null;
  return <div className="attachment-chips">
    {items.map((item) => <span key={item.id} className="attachment-chip" title={item.kind === "document" ? `${item.chars.toLocaleString("pt-BR")} caracteres extraídos` : "Imagem"}>
      {item.kind === "image" ? <ImageIcon size={13} /> : <FileText size={13} />}
      <span>{item.name}</span>
      <button type="button" aria-label={"Remover " + item.name} onClick={() => onRemove(item.id)}><X size={12} /></button>
    </span>)}
  </div>;
}
