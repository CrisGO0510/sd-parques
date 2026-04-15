import os
from server.game.engine import GameEngine
from server.game.constants import SAFE_POSITIONS, HOME_ENTRY


def score_moves(engine: GameEngine, color: str) -> list[dict]:
    total = engine.dice_total()
    scored = []
    for piece in engine.board.pieces[color]:
        if piece.state == "finished":
            continue
        score = 0
        reasons = []
        if piece.state == "jail":
            if engine.is_pair():
                score += 25
                reasons.append("Sacar ficha de la carcel")
            else:
                continue
        elif piece.state in ("board", "home_stretch"):
            original = (piece.state, piece.position, piece.home_position)
            # Snapshot victims
            victims_snapshot = []
            if piece.state == "board":
                new_pos = (piece.position + total) % 68
                for vc, vps in engine.board.pieces.items():
                    if vc == color:
                        continue
                    for vp in vps:
                        if vp.state == "board" and vp.position == new_pos:
                            victims_snapshot.append((vp, vp.state, vp.position))
            result = engine.board.move_piece(color, piece.index, total)
            new_pos = piece.position
            new_state = piece.state
            # Revert
            piece.state, piece.position, piece.home_position = original
            for vp, vs, vpos in victims_snapshot:
                vp.state = vs
                vp.position = vpos
            if result["action"] == "invalid":
                continue
            if result["action"] == "eat":
                score += 50
                reasons.append("Comer ficha rival")
            if result["action"] == "finish":
                score += 60
                reasons.append("Llevar ficha a la meta")
            if result["action"] == "enter":
                score += 40
                reasons.append("Entrar a la recta final")
            if new_state == "board" and new_pos in SAFE_POSITIONS:
                score += 30
                reasons.append("Llegar a casilla segura")
            if piece.state == "board":
                for rival_color, rival_pieces in engine.board.pieces.items():
                    if rival_color == color:
                        continue
                    for rp in rival_pieces:
                        if rp.state == "board":
                            dist = (piece.position - rp.position) % 68
                            if 1 <= dist <= 12:
                                score += 20
                                reasons.append("Mover ficha en riesgo")
                                break
            if score == 0:
                score += 15
                reasons.append("Avanzar ficha")
        scored.append({
            "piece_index": piece.index,
            "score": score,
            "reasons": reasons,
            "state": piece.state,
        })
    scored.sort(key=lambda x: x["score"], reverse=True)
    return scored


def get_fallback_explanation(best_move: dict) -> str:
    reasons = best_move.get("reasons", [])
    piece = best_move.get("piece_index", 0)
    if not reasons:
        return f"Te recomiendo mover la ficha {piece + 1}."
    main_reason = reasons[0]
    return f"Te recomiendo mover la ficha {piece + 1}: {main_reason.lower()}."


def get_llm_explanation(engine: GameEngine, color: str, best_move: dict) -> str:
    api_key = os.getenv("CLAUDE_API_KEY", "")
    if not api_key:
        return get_fallback_explanation(best_move)
    try:
        import anthropic

        client = anthropic.Anthropic(api_key=api_key)
        board_state = engine.get_state()
        prompt = (
            f"Eres un asistente de juego de Parques colombiano. "
            f"Analiza el estado del tablero y recomienda la mejor jugada.\n\n"
            f"Estado actual:\n"
            f"- Jugador: {color}\n"
            f"- Dados: {engine.dice[0]} y {engine.dice[1]} "
            f"(total: {engine.dice_total()})\n"
            f"- Jugada recomendada: mover ficha {best_move['piece_index'] + 1}\n"
            f"- Razones del analisis: {', '.join(best_move['reasons'])}\n"
            f"- Puntaje: {best_move['score']}\n\n"
            f"Explica en 1-2 oraciones por que esta es la mejor jugada. "
            f"Se conciso y usa lenguaje casual."
        )

        message = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=150,
            messages=[{"role": "user", "content": prompt}],
        )
        return message.content[0].text
    except Exception:
        return get_fallback_explanation(best_move)


def get_recommendation(engine: GameEngine, color: str) -> dict:
    scored = score_moves(engine, color)
    if not scored:
        return {
            "recommendation": None,
            "explanation": "No hay jugadas disponibles.",
        }
    best = scored[0]
    explanation = get_fallback_explanation(best)
    return {
        "recommendation": {
            "piece_index": best["piece_index"],
            "score": best["score"],
            "reasons": best["reasons"],
        },
        "explanation": explanation,
        "all_moves": scored,
    }
