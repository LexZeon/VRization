import MetalKit
import CoreFoundation
import CoreGraphics
import VRizationCore
#if STEAMVR_PREVIEW
import VRizationSteamVRCore
#endif

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
#if STEAMVR_PREVIEW
    private var streamSession: StreamSession?
    func setStreamSession(_ session: StreamSession?) {
        lock.lock(); streamSession = session; texture = nil; pose = Pose(); textureInfo = "no texture"; lock.unlock()
    }
#endif
    private struct Uniforms {
        var optics: SIMD4<Float>
        var placement: SIMD4<Float>
        var scene: SIMD4<Float>
        var flags: SIMD4<Float>
        var sampling: SIMD4<Float>
        var uvBounds: SIMD4<Float>
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
#if STEAMVR_PREVIEW
        lock.lock(); let sessionDescriptor = streamSession; lock.unlock()
        guard let sessionDescriptor = sessionDescriptor, sessionDescriptor.accepted,
              sessionDescriptor.streamLayout != .sbs || image.width % 2 == 0 else { throw RendererError.invalidRaster }
#endif
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
        lock.lock(); let currentTexture = texture, profile = settings, p = pose
#if STEAMVR_PREVIEW
        let descriptor = streamSession
#endif
        lock.unlock()
#if STEAMVR_PREVIEW
        let layout = descriptor?.streamLayout ?? .mono
        let s = SteamVRGeometry.renderSettings(profile, layout: layout)
#else
        let s = profile
#endif
        if let currentTexture = currentTexture {
            encoder.setRenderPipelineState(pipeline)
            encoder.setFragmentTexture(currentTexture, index: 0)
            let width = drawable.texture.width, height = drawable.texture.height, leftWidth = width / 2
            if width >= 2 && height > 0 {
                for eye in 0..<2 {
                    let eyeWidth = eye == 0 ? leftWidth : width - leftWidth
                    let sign: Float = eye == 0 ? -1 : 1
                    var contentAspect = Double(currentTexture.width) / Double(currentTexture.height)
                    var sampling = SIMD4<Float>(0, 1, 0, 0)
                    var uvBounds = SIMD4<Float>(0, 0, 1, 1)
#if STEAMVR_PREVIEW
                    guard let eyeSampling = try? StereoEyeSampling.resolve(width: currentTexture.width,
                        height: currentTexture.height, eye: eye, layout: layout) else { continue }
                    contentAspect = eyeSampling.contentAspect
                    sampling = SIMD4(Float(eyeSampling.uvOriginX), Float(eyeSampling.uvScaleX), 0, 0)
                    uvBounds = SIMD4(Float(eyeSampling.uvMinimum.x), Float(eyeSampling.uvMinimum.y),
                                     Float(eyeSampling.uvMaximum.x), Float(eyeSampling.uvMaximum.y))
#endif
                    let resolved = (try? HeadsetFit.resolvedFit(settings: s,
                        imageAspect: contentAspect,
                        eyeAspect: Double(eyeWidth) / Double(height))) ?? s
                    var u = Uniforms(
                        optics: SIMD4(Float(eyeWidth) / Float(height), s.mode == "fps_enhanced" ? 1 : Float(contentAspect), Float(resolved.scale), Float(resolved.offsetX)),
                        placement: SIMD4(Float(resolved.offsetY), Float(resolved.eyeSeparation) * sign, Float(s.distortion), Float(s.fov)),
                        scene: SIMD4(Float(s.distance), Float(p.yaw), Float(p.pitch), Float(p.roll)),
                        flags: SIMD4(s.mode == "cinema" ? 1 : 0, sign, s.mode == "fps_enhanced" ? 1 : 0, 0),
                        sampling: sampling, uvBounds: uvBounds)
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
