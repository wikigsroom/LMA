package com.lma.app;
import java.util.*;
/** Host adapter: does not stand in as proof of a real Android foreground Service. */
public final class LmaService {
    public EngineHost engine;
    public final List<String> installed = Collections.synchronizedList(new ArrayList<>());
    public void activityChanged() {}
    public void updateNotification() {}
    public void modelInstalled(String id) { installed.add(id); }
}
