from __future__ import annotations

import unittest

from app.conversation import (
    Choice,
    ChoiceNotFound,
    ConversationState,
    ConversationStore,
    RequiredRequisite,
    resolve_choice,
)


class ChoiceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.choices = (
            Choice(id="memo", label="Служебная записка"),
            Choice(id="letter", label="Письмо"),
        )

    def test_choice_can_be_resolved_by_number_id_or_label(self) -> None:
        self.assertEqual(resolve_choice(self.choices, "2").id, "letter")
        self.assertEqual(resolve_choice(self.choices, "MEMO").id, "memo")
        self.assertEqual(
            resolve_choice(self.choices, "служебная записка").id,
            "memo",
        )

    def test_unknown_choice_is_rejected(self) -> None:
        with self.assertRaises(ChoiceNotFound):
            resolve_choice(self.choices, "99")


class ConversationStoreTests(unittest.TestCase):
    def test_complete_fsm_path_resets_chat(self) -> None:
        store = ConversationStore()
        doc_type = Choice(
            id="memo",
            label="Служебная записка",
            required_requisites=(RequiredRequisite("doc_date", "Дата"),),
        )
        template = Choice(id="classic", label="Классический")

        store.start(42, "Черновик", (doc_type,))
        self.assertEqual(store.state(42), ConversationState.WAITING_DOC_TYPE)
        selected_type = store.resolve_doc_type(42, "1")
        store.select_doc_type(42, selected_type, (template,))
        self.assertEqual(store.state(42), ConversationState.WAITING_TEMPLATE)
        request = store.begin_generation(42, store.resolve_template(42, "classic"))
        self.assertEqual(store.state(42), ConversationState.PROCESSING)
        self.assertEqual(request.doc_type_id, "memo")
        self.assertEqual(request.template_id, "classic")
        self.assertTrue(store.complete(42, request.generation_id))
        self.assertEqual(store.state(42), ConversationState.WAITING_DRAFT)

    def test_stale_generation_cannot_reset_new_conversation(self) -> None:
        store = ConversationStore()
        doc_type = Choice(id="memo", label="Memo")
        template = Choice(id="classic", label="Classic")
        store.start(7, "old", (doc_type,))
        store.select_doc_type(7, doc_type, (template,))
        old = store.begin_generation(7, template)

        store.reset(7)
        store.start(7, "new", (doc_type,))
        self.assertFalse(store.complete(7, old.generation_id))
        self.assertEqual(store.state(7), ConversationState.WAITING_DOC_TYPE)


if __name__ == "__main__":
    unittest.main()
