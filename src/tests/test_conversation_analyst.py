"""Tests for the warm conversation analyst agent."""

from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock

import pytest

from agents.conversation_analyst_agent import (
    analyze_batch,
    analyze_summary,
    classify_trigger,
)
from models.schemas import (
    ContactConversationSummary,
    ConversationMessage,
    ConversationThread,
    FollowUpTrigger,
)


@pytest.fixture(autouse=True)
def _use_tmp_outputs(tmp_path, monkeypatch):
    monkeypatch.setenv("OUTPUTS_DIR", str(tmp_path / "outputs"))


def _build_summary(
    contact_id: str = "c-1",
    *,
    email: str = "jane@acme.com",
    last_inbound_delta_days: int | None = 1,
    last_outbound_delta_days: int | None = 2,
    latest_direction: str = "inbound",
    latest_delta_hours: int = 4,
) -> ContactConversationSummary:
    now = datetime.now(timezone.utc)
    latest_ts = (now - timedelta(hours=latest_delta_hours)).isoformat()
    inbound_ts = (
        (now - timedelta(days=last_inbound_delta_days)).isoformat()
        if last_inbound_delta_days is not None
        else None
    )
    outbound_ts = (
        (now - timedelta(days=last_outbound_delta_days)).isoformat()
        if last_outbound_delta_days is not None
        else None
    )

    oldest_ts = (now - timedelta(days=max(last_outbound_delta_days or 0, last_inbound_delta_days or 0, 3) + 2)).isoformat()
    older_direction = "outbound" if latest_direction == "inbound" else "inbound"
    messages = [
        ConversationMessage(
            messageId="older",
            conversationId="conv-1",
            direction=older_direction,
            body="Earlier message",
            timestamp=oldest_ts,
            messageType="Email",
        ),
        ConversationMessage(
            messageId="latest",
            conversationId="conv-1",
            direction=latest_direction,
            body="Latest message",
            timestamp=latest_ts,
            messageType="Email",
        ),
    ]
    messages.sort(key=lambda message: message.timestamp, reverse=True)

    return ContactConversationSummary(
        contactId=contact_id,
        ghlContactId=f"ghl-{contact_id}",
        firstName="Jane",
        lastName="Doe",
        email=email,
        companyName="Acme",
        title="VP Revenue",
        threads=[
            ConversationThread(
                conversationId="conv-1",
                contactId=contact_id,
                lastMessageDate=messages[0].timestamp,
                messageCount=len(messages),
                messages=messages,
            )
        ],
        totalMessages=len(messages),
        lastInboundDate=inbound_ts,
        lastOutboundDate=outbound_ts,
        scannedAt=now.isoformat(),
    )


class TestTriggerClassification:
    def test_classify_trigger_awaiting_our_response(self):
        summary = _build_summary(latest_direction="inbound", last_inbound_delta_days=0, last_outbound_delta_days=2)
        trigger, reason = classify_trigger(summary)
        assert trigger == FollowUpTrigger.AWAITING_OUR_RESPONSE
        assert "owe the next response" in reason

    def test_classify_trigger_no_reply(self):
        summary = _build_summary(
            latest_direction="outbound",
            last_inbound_delta_days=None,
            last_outbound_delta_days=3,
            latest_delta_hours=72,
        )
        trigger, reason = classify_trigger(summary)
        assert trigger == FollowUpTrigger.NO_REPLY
        assert "unanswered" in reason

    def test_classify_trigger_gone_cold(self):
        summary = _build_summary(
            latest_direction="outbound",
            last_inbound_delta_days=12,
            last_outbound_delta_days=9,
            latest_delta_hours=24 * 9,
        )
        trigger, reason = classify_trigger(summary)
        assert trigger == FollowUpTrigger.GONE_COLD
        assert "two-way engagement" in reason


class TestAnalyzeSummary:
    @pytest.mark.asyncio
    async def test_skips_ineligible_summary_without_model_call(self):
        client = AsyncMock()
        summary = _build_summary(email="")

        result = await analyze_summary(summary, client=client)

        assert result is None
        client.complete_json.assert_not_called()

    @pytest.mark.asyncio
    async def test_analyze_summary_writes_output(self, tmp_path):
        client = AsyncMock()
        client.complete_json = AsyncMock(return_value={
            "sentiment": "positive",
            "stage": "engaged",
            "urgency": "hot",
            "keyTopics": ["pricing", "implementation"],
            "recommendedAction": "Reply with a concrete next step.",
            "conversationSummary": "The contact is engaged and asked for next steps.",
        })
        summary = _build_summary()

        analysis = await analyze_summary(summary, client=client)

        assert analysis is not None
        assert analysis.contact_id == "c-1"
        assert analysis.source_conversation_id == "conv-1"
        assert analysis.trigger == FollowUpTrigger.AWAITING_OUR_RESPONSE
        assert analysis.key_topics == ["pricing", "implementation"]

        analysis_path = tmp_path / "outputs" / "conversation_analysis" / "c-1.json"
        assert analysis_path.exists()
        persisted = json.loads(analysis_path.read_text(encoding="utf-8"))
        assert persisted["sourceConversationId"] == "conv-1"
        assert persisted["triggerReason"]

    @pytest.mark.asyncio
    async def test_analyze_batch_isolates_failures(self, tmp_path):
        good_summary = _build_summary(contact_id="c-good")
        bad_summary = _build_summary(contact_id="c-bad")

        client = AsyncMock()

        async def _side_effect(*args, **kwargs):
            trace = kwargs.get("trace_context", {})
            if trace.get("contactId") == "c-bad":
                raise ValueError("Malformed JSON")
            return {
                "sentiment": "neutral",
                "stage": "engaged",
                "urgency": "warm",
                "keyTopics": ["timeline"],
                "recommendedAction": "Send a short nudge.",
                "conversationSummary": "The contact has gone quiet.",
            }

        client.complete_json = AsyncMock(side_effect=_side_effect)

        result = await analyze_batch(
            [good_summary, bad_summary],
            client=client,
            max_concurrent=2,
        )

        assert len(result.analyses) == 1
        assert result.analyses[0].contact_id == "c-good"
        assert result.failed == 1
        assert result.errors == ["c-bad: Malformed JSON"]

        index_path = tmp_path / "outputs" / "conversation_analysis" / "index.json"
        assert index_path.exists()
