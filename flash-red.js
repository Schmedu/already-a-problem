ObjC.import('Cocoa');

function run() {
  var styleMaskBorderless = 0;
  var backingBuffered = 2;

  var screens = $.NSScreen.screens;
  var count = screens.count;
  var wins = [];
  for (var s = 0; s < count; s++) {
    var frame = screens.objectAtIndex(s).frame;
    var win = $.NSWindow.alloc.initWithContentRectStyleMaskBackingDefer(
      frame, styleMaskBorderless, backingBuffered, false
    );
    win.opaque = false;
    win.hasShadow = false;
    win.ignoresMouseEvents = true;
    win.level = 1000; // above normal windows, below screensaver
    // CanJoinAllSpaces (1) | Stationary (16) | FullScreenAuxiliary (256)
    win.collectionBehavior = 273;
    win.orderFront(null);
    wins.push(win);
  }

  var steps = 12;
  var peakAlpha = 0.38;
  for (var i = 0; i <= steps; i++) {
    var a = peakAlpha * (1 - i / steps);
    var color = $.NSColor.colorWithCalibratedRedGreenBlueAlpha(1, 0, 0, a);
    for (var w = 0; w < wins.length; w++) {
      wins[w].backgroundColor = color;
    }
    // setting backgroundColor already marks each window as needing display;
    // delay() doesn't pump Cocoa's run loop, so the window server never
    // actually gets the flush - spin the run loop briefly instead
    $.NSRunLoop.currentRunLoop.runUntilDate($.NSDate.dateWithTimeIntervalSinceNow(0.03));
  }
  // process exits right after run() returns, which tears the windows down;
  // win.close() isn't reliably bridged here, so skip it
}
