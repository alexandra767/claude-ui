import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { ArrowLeft, Download, Maximize2, Trash2 } from 'lucide-react';

interface ImageFile {
  name: string;
  url: string;
}

export default function Gallery() {
  const navigate = useNavigate();
  const [images, setImages] = useState<ImageFile[]>([]);
  const [selected, setSelected] = useState<string | null>(null);

  useEffect(() => {
    loadImages();
  }, []);

  const loadImages = async () => {
    try {
      const token = localStorage.getItem('token');
      const res = await fetch('/api/gallery', {
        headers: token ? { Authorization: `Bearer ${token}` } : {},
      });
      if (res.ok) {
        const data = await res.json();
        setImages(data.images || []);
      }
    } catch {}
  };

  return (
    <div className="min-h-screen bg-cream">
      <div className="bg-white border-b border-border">
        <div className="max-w-5xl mx-auto px-6 py-4 flex items-center gap-4">
          <button onClick={() => navigate('/')} className="p-2 rounded-lg text-text-secondary hover:text-text-primary hover:bg-cream transition">
            <ArrowLeft className="w-5 h-5" />
          </button>
          <div>
            <h1 className="text-lg font-semibold text-text-primary">Image Gallery</h1>
            <p className="text-xs text-text-secondary">{images.length} generated images</p>
          </div>
        </div>
      </div>

      <div className="max-w-5xl mx-auto px-6 py-6">
        {images.length === 0 ? (
          <div className="text-center py-16 text-text-secondary">
            No images generated yet. Ask the AI to create an image to get started.
          </div>
        ) : (
          <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-4">
            {images.map((img) => (
              <div key={img.name} className="group relative rounded-xl overflow-hidden border border-border bg-white aspect-square">
                <img
                  src={img.url}
                  alt={img.name}
                  className="w-full h-full object-cover cursor-pointer"
                  onClick={() => setSelected(img.url)}
                />
                <div className="absolute top-2 right-2 flex gap-1 opacity-0 group-hover:opacity-100 transition">
                  <a href={img.url} download={img.name} className="p-1.5 rounded-lg bg-black/50 text-white hover:bg-black/70 transition">
                    <Download className="w-3.5 h-3.5" />
                  </a>
                  <button onClick={() => setSelected(img.url)} className="p-1.5 rounded-lg bg-black/50 text-white hover:bg-black/70 transition">
                    <Maximize2 className="w-3.5 h-3.5" />
                  </button>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Lightbox */}
      {selected && (
        <div className="fixed inset-0 bg-black/80 z-50 flex items-center justify-center p-8" onClick={() => setSelected(null)}>
          <img src={selected} alt="" className="max-w-full max-h-full object-contain rounded-xl" />
        </div>
      )}
    </div>
  );
}
