// Reproducible vector drawing for the independent TG Classic app icon.
import CoreGraphics
import CoreText
import ImageIO
import Foundation

let size = 1024
let context = CGContext(data: nil, width: size, height: size, bitsPerComponent: 8,
    bytesPerRow: size * 4, space: CGColorSpaceCreateDeviceRGB(),
    bitmapInfo: CGImageAlphaInfo.premultipliedLast.rawValue)!
func color(_ hex: UInt32) -> CGColor {
    CGColor(red: CGFloat((hex >> 16) & 255) / 255,
        green: CGFloat((hex >> 8) & 255) / 255,
        blue: CGFloat(hex & 255) / 255, alpha: 1)
}
func fill(_ rect: CGRect, _ hex: UInt32) {
    context.setFillColor(color(hex)); context.fill(rect)
}
func frame(_ rect: CGRect, _ sunken: Bool = false) {
    let colors: [UInt32] = sunken ? [0x808080, 0xffffff, 0x404040, 0xdfdfdf]
        : [0xffffff, 0x404040, 0xdfdfdf, 0x808080]
    for i in 0...1 {
        let r = rect.insetBy(dx: CGFloat(i * 8), dy: CGFloat(i * 8))
        fill(CGRect(x: r.minX, y: r.maxY - 8, width: r.width, height: 8), colors[i * 2])
        fill(CGRect(x: r.minX, y: r.minY, width: 8, height: r.height), colors[i * 2])
        fill(CGRect(x: r.minX + 8, y: r.minY, width: r.width - 8, height: 8), colors[i * 2 + 1])
        fill(CGRect(x: r.maxX - 8, y: r.minY, width: 8, height: r.height - 8), colors[i * 2 + 1])
    }
}
func text(_ value: String, _ fontSize: CGFloat, _ x: CGFloat, _ y: CGFloat, _ hex: UInt32) {
    let font = CTFontCreateWithName("Arial-BoldMT" as CFString, fontSize, nil)
    let line = CTLineCreateWithAttributedString(NSAttributedString(string: value, attributes: [
        NSAttributedString.Key(kCTFontAttributeName as String): font,
        NSAttributedString.Key(kCTForegroundColorAttributeName as String): color(hex)
    ]))
    context.textPosition = CGPoint(x: x, y: y)
    CTLineDraw(line, context)
}
fill(CGRect(x: 0, y: 0, width: size, height: size), 0xc0c0c0)
frame(CGRect(x: 8, y: 8, width: 1008, height: 1008))
fill(CGRect(x: 38, y: 792, width: 948, height: 190), 0x000080)
text("TG Classic", 116, 72, 846, 0xffffff)
let panel = CGRect(x: 70, y: 248, width: 884, height: 490)
fill(panel, 0xffffff); frame(panel, true)
text("TG", 340, 252, 354, 0x000080)
let button = CGRect(x: 216, y: 74, width: 592, height: 120)
fill(button, 0xc0c0c0); frame(button)
text("CLASSIC", 74, 340, 106, 0x000000)
let output = URL(fileURLWithPath: CommandLine.arguments[1])
let destination = CGImageDestinationCreateWithURL(output as CFURL, "public.png" as CFString, 1, nil)!
CGImageDestinationAddImage(destination, context.makeImage()!, nil)
precondition(CGImageDestinationFinalize(destination))
