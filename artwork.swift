import Foundation
import AppKit

typealias MRNowPlayingInfoCallback = @convention(c) (DispatchQueue, @escaping ([String: AnyObject]?) -> Void) -> Void

let handle = dlopen("/System/Library/PrivateFrameworks/MediaRemote.framework/MediaRemote", RTLD_NOW)
guard handle != nil else {
    fatalError("❌ Failed to load MediaRemote.framework")
}

guard let sym = dlsym(handle, "MRMediaRemoteGetNowPlayingInfo") else {
    fatalError("❌ Could not find symbol MRMediaRemoteGetNowPlayingInfo")
}

let getNowPlayingInfo = unsafeBitCast(sym, to: MRNowPlayingInfoCallback.self)

func resizeImage(_ data: Data, to size: NSSize) -> Data? {
    guard let image = NSImage(data: data) else { return nil }

    let targetRect = NSRect(origin: .zero, size: size)
    let rep = NSBitmapImageRep(
        bitmapDataPlanes: nil,
        pixelsWide: Int(size.width),
        pixelsHigh: Int(size.height),
        bitsPerSample: 8,
        samplesPerPixel: 4,
        hasAlpha: true,
        isPlanar: false,
        colorSpaceName: .deviceRGB,
        bytesPerRow: 0,
        bitsPerPixel: 0
    )

    rep?.size = size

    NSGraphicsContext.saveGraphicsState()
    if let context = rep.flatMap(NSGraphicsContext.init(bitmapImageRep:)) {
        NSGraphicsContext.current = context
        context.imageInterpolation = .high
        image.draw(in: targetRect, from: .zero, operation: .copy, fraction: 1.0)
        context.flushGraphics()
    }
    NSGraphicsContext.restoreGraphicsState()

    return rep?.representation(using: .png, properties: [:])
}

func saveArtwork(_ info: [String: AnyObject]) {
    if let artworkData = info["kMRMediaRemoteNowPlayingInfoArtworkData"] as? Data {
        print(artworkData.base64EncodedString())
    } else {
        print("❌ No artwork data found")
    }
}

Timer.scheduledTimer(withTimeInterval: 1.0, repeats: true) { _ in
    getNowPlayingInfo(DispatchQueue.main) { info in
        guard let info = info else {
            print("⏸ No now playing info available.")
            return
        }
        saveArtwork(info)
    }
}

let sigintSource = DispatchSource.makeSignalSource(signal: SIGINT, queue: .main)
signal(SIGINT, SIG_IGN)
sigintSource.setEventHandler {
    print("👋 Exiting on Ctrl+C")
    exit(0)
}
sigintSource.resume()

RunLoop.main.run()