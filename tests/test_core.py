from src.core.controller import MensajeEntrada, RespuestaSalida


def test_core_message_contracts_have_safe_defaults() -> None:
    message = MensajeEntrada("hola")
    response = RespuestaSalida("request-123", "respuesta")

    assert message.origen == "interfaz_interna"
    assert response.simulada is False
