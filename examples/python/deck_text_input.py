"""Open Steam's floating keyboard in a Pygame window and edit a chat draft."""

import pygame
from pygame._sdl2 import controller

import steamworks


def run():
    screen = pygame.display.set_mode((640, 300))
    pygame.display.set_caption("Steam floating keyboard")
    font = pygame.font.Font(None, 28)
    clock = pygame.time.Clock()
    field = pygame.Rect(24, 75, 592, 45)
    callbacks = steamworks.ClientCallbacks()
    controllers = {}

    def add_controller(index):
        if controller.is_controller(index):
            device = controller.Controller(index)
            controllers[device.as_joystick().get_instance_id()] = device

    for index in range(controller.get_count()):
        add_controller(index)

    editing = False
    closing = False
    draft = ""
    status = "Select chat with A, a click, or Return."

    def on_dismissed(_event):
        nonlocal editing, closing, draft, status
        if not editing:
            return
        if not closing:
            status = "Chat canceled. Gamepad focus restored."
        editing = closing = False
        draft = ""
        pygame.key.stop_text_input()

    callbacks.register(steamworks.FloatingGamepadTextInputDismissed, on_dismissed)
    pygame.key.stop_text_input()

    def open_chat():
        nonlocal editing, status
        pygame.key.set_text_input_rect(field)
        pygame.key.start_text_input()
        editing = steamworks.utils.show_floating_gamepad_text_input(
            steamworks.EFloatingGamepadTextInputMode.SingleLine,
            field.x, field.y, field.width, field.height,
        )
        if editing:
            status = "Return submits. Escape or B cancels."
        else:
            pygame.key.stop_text_input()
            status = "Steam could not show the keyboard. Chat remains selected."

    def finish_chat(submit):
        nonlocal closing, status
        if submit and draft.strip():
            print(f"Submitted: {draft}")
            status = "Chat submitted. Gamepad focus restored on dismissal."
        else:
            status = "Chat canceled. Gamepad focus restored on dismissal."
        closing = True
        steamworks.utils.dismiss_floating_gamepad_text_input()

    while True:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                if editing:
                    steamworks.utils.dismiss_floating_gamepad_text_input()
                return
            if event.type == pygame.CONTROLLERDEVICEADDED:
                add_controller(event.device_index)
            if event.type == pygame.CONTROLLERDEVICEREMOVED:
                controllers.pop(event.instance_id, None)

            confirm = event.type == pygame.CONTROLLERBUTTONDOWN and event.button == pygame.CONTROLLER_BUTTON_A
            cancel = event.type == pygame.CONTROLLERBUTTONDOWN and event.button == pygame.CONTROLLER_BUTTON_B
            enter = event.type == pygame.KEYDOWN and event.key in (pygame.K_RETURN, pygame.K_KP_ENTER)
            escape = event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE
            click_chat = event.type == pygame.MOUSEBUTTONDOWN and field.collidepoint(event.pos)
            if editing and not closing:
                if event.type == pygame.TEXTINPUT:
                    draft += event.text
                elif event.type == pygame.KEYDOWN and event.key == pygame.K_BACKSPACE:
                    draft = draft[:-1]
                elif enter or cancel or escape:
                    finish_chat(enter)
            elif not editing and (confirm or enter or click_chat):
                open_chat()

        callbacks.pump()
        screen.fill("#202634")
        pygame.draw.rect(screen, "#394962" if editing else "#303a4d", field)
        pygame.draw.rect(screen, "#93c8ff", field, width=2)
        screen.blit(font.render("Chat", True, "white"), (24, 40))
        screen.blit(font.render(draft[-50:] if editing else "Open chat", True, "white"), (35, 87))
        screen.blit(font.render(status, True, "white"), (24, 145))
        pygame.display.flip()
        clock.tick(60)


def main():
    pygame.init()
    controller.init()
    controller.set_eventstate(True)
    try:
        if steamworks.init_ex():
            raise SystemExit(steamworks.last_init_error())
        try:
            run()
        finally:
            steamworks.shutdown()
    finally:
        pygame.quit()


if __name__ == "__main__":
    main()
