// 사진을 올리기 전에 브라우저에서 줄임 (결정 29)
// - 원본: 긴 변 1600px JPEG — 휴대폰 사진(수 MB)을 수백 KB로. 캔버스로 다시 그리므로 위치 등 사진 정보(EXIF)도 빠짐
// - 썸네일: 긴 변 360px JPEG — 대화 목록에서는 이것만 불러옴
// 브라우저가 읽지 못하는 형식(예: 일부 HEIC)이면 null → 원본 그대로 올림
const MAIN_EDGE = 1600;
const THUMB_EDGE = 360;

async function draw(bitmap: ImageBitmap, edge: number, quality: number): Promise<Blob | null> {
  const scale = Math.min(1, edge / Math.max(bitmap.width, bitmap.height));
  const canvas = document.createElement('canvas');
  canvas.width = Math.max(1, Math.round(bitmap.width * scale));
  canvas.height = Math.max(1, Math.round(bitmap.height * scale));
  const ctx = canvas.getContext('2d');
  if (!ctx) return null;
  ctx.fillStyle = '#fff'; // 투명 PNG를 JPEG로 바꿀 때 검은 배경이 되지 않게
  ctx.fillRect(0, 0, canvas.width, canvas.height);
  ctx.drawImage(bitmap, 0, 0, canvas.width, canvas.height);
  return new Promise((resolve) => canvas.toBlob(resolve, 'image/jpeg', quality));
}

export async function shrinkImage(file: Blob): Promise<{ main: Blob; thumb: Blob } | null> {
  let bitmap: ImageBitmap;
  try {
    bitmap = await createImageBitmap(file, { imageOrientation: 'from-image' }); // 세로 사진이 눕지 않게
  } catch {
    return null;
  }
  try {
    const [main, thumb] = await Promise.all([draw(bitmap, MAIN_EDGE, 0.82), draw(bitmap, THUMB_EDGE, 0.7)]);
    return main && thumb ? { main, thumb } : null;
  } finally {
    bitmap.close();
  }
}

// 확장자를 .jpg로 (화면에 보이는 이름용, 경로에는 쓰지 않음)
export const asJpgName = (name: string) => (name.replace(/\.[A-Za-z0-9]{1,5}$/, '') || 'photo') + '.jpg';
