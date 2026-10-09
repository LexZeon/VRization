import MetalKit
import CoreFoundation
import CoreGraphics
import VRizationCore

/// Metal resources are bounded: one current texture and at most two GPU submissions.
final class StereoRenderer: NSObject, MTKViewDelegate {
    private let device: MTLDevice
    private let commands: MTLCommandQueue
    private let pipeline: MTLRenderPipelineState
    private let inFlight = DispatchSemaphore(value: 2)
    private let lock = NSLock()
    private var texture: MTLTexture?
    private var settings = VRSettings()
    private var pose = Pose()
    private var textureInfo = "no texture"
    private struct Uniforms {
        var optics: SIMD4<Float>
        var placement: SIMD4<Float>
        var scene: SIMD4<Float>
        var flags: SIMD4<Float>
    }

    init(view: MTKView) throws {
        guard let device = view.device, let commands = device.makeCommandQueue(),
              let library = device.makeDefaultLibrary() else { throw RendererError.unavailable }
        self.device = device; self.commands = commands
        let description = MTLRenderPipelineDescriptor()
        description.vertexFunction = library.makeFunction(name: "stereoVertex")
        description.fragmentFunction = library.makeFunction(name: "stereoFragment")
        description.colorAttachments[0].pixelFormat = view.colorPixelFormat
        pipeline = try device.makeRenderPipelineState(descriptor: description)
        super.init()
        view.clearColor = MTLClearColorMake(0, 0, 0, 1)
        view.preferredFramesPerSecond = 60
        view.delegate = self
    }
    enum RendererError: Error { case unavailable, invalidRaster }

    func setSettings(_ settings: VRSettings) {
        lock.lock(); self.settings = settings; lock.unlock()
    }
    func setPose(_ pose: Pose) { lock.lock(); self.pose = pose; lock.unlock() }
    func submit(_ image: CGImage) throws {
        guard image.width > 0, image.height > 0, image.width <= 2048, image.height <= 2048,
              image.bitsPerComponent == 8, image.bitsPerPixel == 32, image.alphaInfo == .premultipliedLast,
              (image.bitmapInfo.rawValue & CGBitmapInfo.byteOrderMask.rawValue) == CGBitmapInfo.byteOrder32Big.rawValue,
              image.bytesPerRow >= image.width * 4, let bytes = image.dataProvider?.data,
              CFDataGetLength(bytes) >= image.bytesPerRow * image.height, let pointer = CFDataGetBytePtr(bytes) else {
            throw RendererError.invalidRaster
        }
        let descriptor = MTLTextureDescriptor.texture2DDescriptor(pixelFormat: .rgba8Unorm,
            width: image.width, height: image.height, mipmapped: false)
        descriptor.usage = .shaderRead
        descriptor.storageMode = .shared
        guard let next = device.makeTexture(descriptor: descriptor) else { throw RendererError.unavailable }
        // JPEGDecoder provides sRGB-encoded, opaque RGBA8. Both texture and
        // drawable use unorm, so the screen receives the same encoded RGB.
        withExtendedLifetime(bytes) {
            next.replace(region: MTLRegionMake2D(0, 0, image.width, image.height), mipmapLevel: 0,
                         withBytes: pointer, bytesPerRow: image.bytesPerRow)
        }
        lock.lock()
        texture = next
        textureInfo = "cg=\(image.bitsPerComponent)/\(image.bitsPerPixel), bitmap=\(image.bitmapInfo.rawValue), row=\(image.bytesPerRow), metal=\(next.pixelFormat.rawValue)"
        lock.unlock()
    }
    var diagnostic: String { lock.lock(); defer { lock.unlock() }; return textureInfo }
    func clear() { lock.lock(); texture = nil; pose = Pose(); textureInfo = "no texture"; lock.unlock() }
    func mtkView(_ view: MTKView, drawableSizeWillChange size: CGSize) {}

    func draw(in view: MTKView) {
        guard inFlight.wait(timeout: .now()) == .success else { return }
        var submitted = false
        defer { if !submitted { inFlight.signal() } }
        guard let pass = view.currentRenderPassDescriptor, let drawable = view.currentDrawable,
              let command = commands.makeCommandBuffer(), let encoder = command.makeRenderCommandEncoder(descriptor: pass) else { return }
        lock.lock(); let currentTexture = texture, s = settings, p = pose; lock.unlock()
        if let currentTexture = currentTexture {
            encoder.setRenderPipelineState(pipeline)
            encoder.setFragmentTexture(currentTexture, index: 0)
            let width = drawable.texture.width, height = drawable.texture.height, leftWidth = width / 2
            if width >= 2 && height > 0 {
                for eye in 0..<2 {
                    let eyeWidth = eye == 0 ? leftWidth : width - leftWidth
                    let sign: Float = eye == 0 ? -1 : 1
                    var u = Uniforms(
                        optics: SIMD4(Float(eyeWidth) / Float(height), Float(currentTexture.width) / Float(currentTexture.height), Float(s.scale), Float(s.offsetX)),
                        placement: SIMD4(Float(s.offsetY), Float(s.eyeSeparation) * sign, Float(s.distortion), Float(s.fov)),
                        scene: SIMD4(Float(s.distance), Float(p.yaw), Float(p.pitch), Float(p.roll)),
                        flags: SIMD4(s.mode == "cinema" ? 1 : 0, sign, 0, 0))
                    encoder.setViewport(MTLViewport(originX: eye == 0 ? 0 : Double(leftWidth), originY: 0,
                        width: Double(eyeWidth), height: Double(height), znear: 0, zfar: 1))
                    encoder.setFragmentBytes(&u, length: MemoryLayout<Uniforms>.stride, index: 0)
                    encoder.drawPrimitives(type: .triangleStrip, vertexStart: 0, vertexCount: 4)
                }
            }
        }
        encoder.endEncoding()
        command.present(drawable)
        let semaphore = inFlight
        command.addCompletedHandler { _ in semaphore.signal() }
        submitted = true
        command.commit()
    }
}
