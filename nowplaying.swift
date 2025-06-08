// Recursively sanitize object for JSON serialization
func sanitizeForJSON(_ object: Any) -> Any {
    if let dict = object as? [String: Any] {
        return dict.mapValues { sanitizeForJSON($0) }
    } else if let array = object as? [Any] {
        return array.map { sanitizeForJSON($0) }
    } else if object is String || object is Int || object is Double || object is Bool || object is NSNull {
        return object
    } else if let date = object as? Date {
        return ISO8601DateFormatter().string(from: date)
    } else {
        return "\(object)"
    }
}
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

func printNowPlayingInfo(_ info: [String: AnyObject]) {
    if UserDefaults.standard.bool(forKey: "PrintRawNowPlayingInfo") {
        print("🎵 Raw Now Playing Info:\n\(info)")
        let rawFileURL = URL(fileURLWithPath: FileManager.default.currentDirectoryPath).appendingPathComponent("nowplaying_raw.json")
        let sanitized = sanitizeForJSON(info)
        if let rawJsonData = try? JSONSerialization.data(withJSONObject: sanitized, options: [.prettyPrinted]) {
            do {
                try rawJsonData.write(to: rawFileURL)
            } catch {
                print("❌ Failed to write raw JSON to file: \(error)")
            }
        }
    }
    if let artworkData = info["kMRMediaRemoteNowPlayingInfoArtworkData"] as? Data {
        let artworkURL = URL(fileURLWithPath: FileManager.default.currentDirectoryPath).appendingPathComponent("static/images/cover.png")
        // Only write artwork if it has changed
        if let existingData = try? Data(contentsOf: artworkURL),
           let resizedExisting = resizeImage(existingData, to: NSSize(width: 3000, height: 3000)),
           let resizedIncoming = resizeImage(artworkData, to: NSSize(width: 3000, height: 3000)),
           resizedExisting == resizedIncoming {
            // Artwork unchanged after resizing, no need to write
        } else {
            if let resizedData = resizeImage(artworkData, to: NSSize(width: 3000, height: 3000)) {
                do {
                    try resizedData.write(to: artworkURL)
                    print("🖼️ Resized artwork saved to \(artworkURL.path)")
                    let lowResURL = URL(fileURLWithPath: FileManager.default.currentDirectoryPath).appendingPathComponent("static/images/cover_low.png")
                    if let lowResData = resizeImage(artworkData, to: NSSize(width: 64, height: 64)) {
                        do {
                            try lowResData.write(to: lowResURL)
                            print("🖼️ Low-res artwork saved to \(lowResURL.path)")
                        } catch {
                            print("❌ Failed to write low-res artwork: \(error)")
                        }
                    } else {
                        print("❌ Failed to resize low-res artwork")
                    }
                } catch {
                    print("❌ Failed to write resized artwork: \(error)")
                }
            } else {
                print("❌ Failed to resize artwork")
            }
        }
    }
    var metadata: [String: Any] = [:]
    if let title = info["kMRMediaRemoteNowPlayingInfoTitle"] {
        metadata["Title"] = title
    }
    if let artist = info["kMRMediaRemoteNowPlayingInfoArtist"] {
        metadata["Artist"] = artist
    }
    if let artistID = info["kMRMediaRemoteNowPlayingInfoArtistiTunesStoreAdamIdentifier"] {
        metadata["Artist ID"] = artistID
    }
    if let album = info["kMRMediaRemoteNowPlayingInfoAlbum"] {
        metadata["Album"] = album
    }
    if let albumID = info["kMRMediaRemoteNowPlayingInfoAlbumiTunesStoreAdamIdentifier"] {
        metadata["Album ID"] = albumID
    }
    if let composer = info["kMRMediaRemoteNowPlayingInfoComposer"] {
        metadata["Composer"] = composer
    }
    if let genre = info["kMRMediaRemoteNowPlayingInfoGenre"] {
        metadata["Genre"] = genre
    }
    if let track = info["kMRMediaRemoteNowPlayingInfoTrackNumber"],
       let total = info["kMRMediaRemoteNowPlayingInfoTotalTrackCount"] {
        metadata["Track"] = "\(track)/\(total)"
    }
    if let duration = info["kMRMediaRemoteNowPlayingInfoDuration"],
       let elapsed = info["kMRMediaRemoteNowPlayingInfoElapsedTime"] {
        metadata["Playback"] = "\(elapsed)/\(duration) seconds"
        if let rate = info["kMRMediaRemoteNowPlayingInfoPlaybackRate"] as? NSNumber {
            metadata["Playback State"] = rate == 1 ? "Playing" : "Paused"
            if let shuffleMode = info["kMRMediaRemoteNowPlayingInfoShuffleMode"] as? Int {
                metadata["Shuffle Mode"] = shuffleMode == 1 ? "On" : "Off"
            }
        }
    }
    if let storeId = info["kMRMediaRemoteNowPlayingInfoiTunesStoreIdentifier"] {
        metadata["iTunes Track ID"] = storeId
    }
    if let timestamp = info["kMRMediaRemoteNowPlayingInfoTimestamp"] as? Date {
        let formatter = ISO8601DateFormatter()
        metadata["Timestamp"] = formatter.string(from: timestamp)
    }

    if let jsonData = try? JSONSerialization.data(withJSONObject: metadata, options: [.prettyPrinted]) {
        let fileURL = URL(fileURLWithPath: FileManager.default.currentDirectoryPath).appendingPathComponent("nowplaying.json")
        do {
            try jsonData.write(to: fileURL)
        } catch {
            print("❌ Failed to write JSON to file: \(error)")
        }
    }
}

Timer.scheduledTimer(withTimeInterval: 1.0, repeats: true) { _ in
    getNowPlayingInfo(DispatchQueue.main) { info in
        guard let info = info else {
            print("⏸ No now playing info available.")
            return
        }
        printNowPlayingInfo(info)
    }
}

let sigintSource = DispatchSource.makeSignalSource(signal: SIGINT, queue: .main)
signal(SIGINT, SIG_IGN)
sigintSource.setEventHandler {
    print("👋 Exiting on Ctrl+C")
    exit(0)
}
sigintSource.resume()

UserDefaults.standard.set(false, forKey: "PrintRawNowPlayingInfo") // Set to false to disable raw printing
RunLoop.main.run()