import Foundation
import ImageIO

/// One active decode, one waiting JPEG and one waiting decoded image, across all sessions.
final class JPEGDecoder {
    var onImage: ((CGImage, UInt64) -> Void)?
    private let queue = DispatchQueue(label: "org.vrization.jpeg", qos: .userInitiated)
    private let lock = NSLock()
    private var generation: UInt64 = 0
    private var pending: (Data, UInt64)?
    private var decoded: (CGImage, UInt64)?
    private var working = false
    private var deliveryPosted = false

    func reset(generation: UInt64) {
        lock.lock(); defer { lock.unlock() }
        self.generation = generation
        pending = nil; decoded = nil
    }

    func submit(_ data: Data, generation: UInt64) {
        guard data.count >= 4, data.count <= 8 * 1024 * 1024 else { return }
        lock.lock()
        guard generation == self.generation else { lock.unlock(); return }
        pending = (data, generation)
        if working { lock.unlock(); return }
        working = true
        lock.unlock()
        queue.async { [weak self] in self?.run() }
    }

    private func run() {
        while true {
            lock.lock()
            guard let job = pending else { working = false; lock.unlock(); return }
            pending = nil
            lock.unlock()
            let image: CGImage? = autoreleasepool {
                guard let source = CGImageSourceCreateWithData(job.0 as CFData, nil),
                      let type = CGImageSourceGetType(source), type as String == "public.jpeg",
                      let metadata = CGImageSourceCopyPropertiesAtIndex(source, 0, nil) as? [CFString: Any],
                      let width = metadata[kCGImagePropertyPixelWidth] as? Int,
                      let height = metadata[kCGImagePropertyPixelHeight] as? Int,
                      width > 0, height > 0, width <= 16384, height <= 16384,
                      Int64(width) * Int64(height) <= 64_000_000 else { return nil }
                let options: [CFString: Any] = [
                    kCGImageSourceCreateThumbnailFromImageAlways: true,
                    kCGImageSourceCreateThumbnailWithTransform: true,
                    kCGImageSourceThumbnailMaxPixelSize: 2048,
                    kCGImageSourceShouldCacheImmediately: true
                ]
                return CGImageSourceCreateThumbnailAtIndex(source, 0, options as CFDictionary)
            }
            guard let image = image else { continue }
            lock.lock()
            guard job.1 == generation else { lock.unlock(); continue }
            decoded = (image, job.1)
            if deliveryPosted { lock.unlock(); continue }
            deliveryPosted = true
            lock.unlock()
            DispatchQueue.main.async { [weak self] in
                guard let self = self else { return }
                self.lock.lock()
                let result = self.decoded
                self.decoded = nil; self.deliveryPosted = false
                let current = self.generation
                self.lock.unlock()
                if let result = result, result.1 == current { self.onImage?(result.0, result.1) }
            }
        }
    }
}
