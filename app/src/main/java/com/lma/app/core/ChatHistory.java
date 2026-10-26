package com.lma.app.core;

import java.util.ArrayList;
import java.util.Collections;
import java.util.List;

/** Keep complete conversational turns so strict chat templates receive alternating roles. */
public final class ChatHistory {
    private ChatHistory() {}
    public static final class Message {
        public final String role, content, status;
        public Message(String role, String content, String status) { this.role = role; this.content = content; this.status = status; }
    }
    public static List<Message> select(List<Message> chronological, int characterBudget, int maxMessages) {
        List<List<Message>> pairs = new ArrayList<>(); Message user = null;
        for (Message message : chronological) {
            if (message.role.equals("user")) { user = message; continue; }
            if (!message.role.equals("assistant") || user == null) continue;
            // A failed/cancelled empty answer must not leave a dangling user turn.
            if (!message.content.trim().isEmpty() && !message.status.equals("generating")) {
                List<Message> pair = new ArrayList<>(); pair.add(user); pair.add(message); pairs.add(pair);
            }
            user = null;
        }
        List<Message> selected = new ArrayList<>(); int budget = Math.max(0, characterBudget);
        for (int i = pairs.size() - 1; i >= 0; i--) {
            List<Message> pair = pairs.get(i); int cost = pair.get(0).content.length() + pair.get(1).content.length();
            if (selected.size() + 2 > maxMessages || cost > budget) break;
            selected.add(pair.get(1)); selected.add(pair.get(0)); budget -= cost;
        }
        Collections.reverse(selected); return selected;
    }
}
