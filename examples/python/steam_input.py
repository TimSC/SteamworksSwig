"""Poll native Steam Input actions defined by your app's Steam Input configuration."""

import argparse
import time

import steamworks


def poll_actions(action_set_name, digital_name, analog_name, show_glyphs=False):
    steam_input = steamworks.input
    steam_input.run_frame(False)
    action_set = steam_input.action_set_handle(action_set_name)
    digital = steam_input.digital_action_handle(digital_name)
    analog = steam_input.analog_action_handle(analog_name)
    if not action_set:
        raise SystemExit(f"Action set unavailable: {action_set_name}")
    if not digital:
        print(f"Digital action unavailable: {digital_name}")
    if not analog:
        print(f"Analog action unavailable: {analog_name}")

    previous = {}
    print("Polling Steam Input. Press Ctrl+C to exit.")
    while True:
        steamworks.run_callbacks()
        steam_input.run_frame(False)
        current = {}
        for controller in steam_input.connected_controllers():
            if controller not in previous:
                steam_input.activate_action_set(controller, action_set)
                print(f"Controller connected: {controller}")
                if show_glyphs:
                    actions = (
                        (digital_name, digital, steam_input.digital_action_origins),
                        (analog_name, analog, steam_input.analog_action_origins),
                    )
                    for name, handle, read_origins in actions:
                        if handle:
                            for origin in read_origins(controller, action_set, handle):
                                print(f"{name} origin {origin}: {steam_input.glyph_for_action_origin_legacy(origin)}")
            was_pressed, old_axes = previous.get(controller, (False, None))

            pressed = False
            if digital:
                state = steam_input.digital_action_data(controller, digital)
                pressed = state.active and state.pressed
                if pressed and not was_pressed:
                    print(f"{controller} {digital_name} pressed")

            axes = None
            if analog:
                state = steam_input.analog_action_data(controller, analog)
                if state.active:
                    axes = (state.mode, round(state.x, 2), round(state.y, 2))
                    if axes != old_axes:
                        print(f"{controller} {analog_name}: {axes}")

            current[controller] = (pressed, axes)

        for controller in previous.keys() - current.keys():
            print(f"Controller disconnected: {controller}")
        previous = current
        time.sleep(1 / 60)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action_set", help="Action set name in your game's configuration")
    parser.add_argument("digital_action", help="Digital action name")
    parser.add_argument("analog_action", help="Analog action name")
    parser.add_argument("--glyphs", action="store_true", help="Print the glyph paths for each new controller")
    args = parser.parse_args()

    if steamworks.init_ex() != 0:
        raise SystemExit(f"Steamworks initialization failed: {steamworks.last_init_error()}")
    try:
        if not steamworks.input.init(True):
            raise SystemExit("Steam Input initialization failed")
        try:
            poll_actions(args.action_set, args.digital_action, args.analog_action, args.glyphs)
        except KeyboardInterrupt:
            pass
        finally:
            steamworks.input.shutdown()
    finally:
        steamworks.shutdown()


if __name__ == "__main__":
    main()
