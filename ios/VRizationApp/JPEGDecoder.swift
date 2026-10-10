import Foundation
import ImageIO
import CoreGraphics
#if STEAMVR_PREVIEW
import VRizationSteamVRCore
#endif

/// One active decode, one waiting JPEG and one waiting decoded image, across all sessions.
final class JPEGDecoder {
    var onImage: ((CGImage, UInt64) -> Void)?
#if STEAMVR_PREVIEW
    var onUnsupportedStereo: ((UInt64) -> Void)?
#endif
    private let queue = DispatchQueue(label: "org.vrization.jpeg", qos: .userInitiated)
    private let lock = NSLock()
    private var generation: UInt64 = 0
    private var pending: (Data, UInt64, Bool)?
    private var decoded: (CGImage, UInt64)?
    private var working = false
    private var deliveryPosted = false

    func reset(generation: UInt64) {
        lock.lock(); defer { lock.unlock() }
        self.generation = generation
        pending = nil; decoded = nil
    }

    func submit(_ data: Data, generation: UInt64, stereo: Bool = false) {
        guard data.count >= 4, data.count <= 8 * 1024 * 1024 else { return }
        lock.lock()
        guard generation == self.generation else { lock.unlock(); return }
        pending = (data, generation, stereo)
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
#if STEAMVR_PREVIEW
                if job.2 {
                    // Packed eyes were resized independently by the host. A
                    // whole-image thumbnail here could mix their shared border
                    // or produce an odd packed width. Decode this raster exactly.
                    let orientation = metadata[kCGImagePropertyOrientation] as? Int ?? 1
                    guard (try? StereoRaster.validate(width: width, height: height, orientation: orientation)) != nil else {
                        DispatchQueue.main.async { [weak self] in
                            guard let self = self else { return }
                            self.lock.lock(); let current = self.generation; self.lock.unlock()
                            if job.1 == current { self.onUnsupportedStereo?(job.1) }
                        }
                        return nil
                    }
                    guard let exact = CGImageSourceCreateImageAtIndex(source, 0,
                        [kCGImageSourceShouldCacheImmediately: true] as CFDictionary) else { return nil }
                    return Self.rgba8(exact)
                }
#endif
                let options: [CFString: Any] = [
                    kCGImageSourceCreateThumbnailFromImageAlways: true,
                    kCGImageSourceCreateThumbnailWithTransform: true,
                    kCGImageSourceThumbnailMaxPixelSize: 2048,
                    kCGImageSourceShouldCacheImmediately: true
                ]
                guard let thumbnail = CGImageSourceCreateThumbnailAtIndex(source, 0, options as CFDictionary) else { return nil }
                return Self.rgba8(thumbnail)
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

    /// ImageIO can return an opaque, skipped-first ARGB image. Make the byte
    /// order explicit on this decode queue before Metal reads the provider.
    /// The resulting CGImage keeps the same top-to-bottom image coordinates.
    private static func rgba8(_ image: CGImage) -> CGImage? {
        guard image.width > 0, image.height > 0, image.width <= 2048, image.height <= 2048,
              let color = CGColorSpace(name: CGColorSpace.sRGB),
              let context = CGContext(data: nil, width: image.width, height: image.height,
                  bitsPerComponent: 8, bytesPerRow: image.width * 4, space: color,
                  bitmapInfo: CGBitmapInfo.byteOrder32Big.rawValue | CGImageAlphaInfo.premultipliedLast.rawValue) else { return nil }
        context.setBlendMode(.copy)
        context.interpolationQuality = .none
        context.draw(image, in: CGRect(x: 0, y: 0, width: CGFloat(image.width), height: CGFloat(image.height)))
        return context.makeImage()
    }
}
