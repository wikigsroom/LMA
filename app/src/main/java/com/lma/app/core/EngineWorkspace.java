package com.lma.app.core;

import java.io.*;
import java.nio.file.*;
import java.nio.file.attribute.BasicFileAttributes;
import java.util.*;

/** Private, disposable filename-preserving hardlinks to leased verified assets. Never copies weights. */
public final class EngineWorkspace implements AutoCloseable {
    public interface Check { void run() throws Exception; }
    private final Path directory;
    private final Check check;
    private final Set<String> names = new HashSet<>();
    private boolean closed;
    public EngineWorkspace(File root, Check check) throws Exception {
        this.check = check; check.run();
        Path parent = root(root);
        directory = Files.createDirectory(parent.resolve("work-" + UUID.randomUUID()));
    }
    private static Path root(File file) throws IOException {
        File expected = new File(file.getAbsoluteFile().getParentFile().getCanonicalFile(), file.getName());
        if (Files.isSymbolicLink(file.toPath()) || !file.getCanonicalFile().equals(expected)) throw new IOException("Engine workspace root is an alias");
        Files.createDirectories(expected.toPath());
        if (!Files.isDirectory(expected.toPath(), LinkOption.NOFOLLOW_LINKS)) throw new IOException("Engine workspace root is not a directory");
        return expected.toPath();
    }
    public File directory() { return directory.toFile(); }
    /** Retain execution filenames until even an unusually slow child has actually exited. */
    public void closeAfter(Process process) throws IOException {
        if (process == null || !process.isAlive()) { close(); return; }
        Thread reaper = new Thread(() -> {
            boolean interrupted = false;
            while (process.isAlive()) try { process.waitFor(); } catch (InterruptedException error) { interrupted = true; }
            try { close(); } catch (IOException error) { /* Startup recovery removes only owned orphan workspaces. */ }
            if (interrupted) Thread.currentThread().interrupt();
        }, "LMA-workspace-reaper"); reaper.setDaemon(true); reaper.start();
    }
    public static String filename(String value) throws IOException {
        if (value == null || !value.matches("[A-Za-z0-9_][A-Za-z0-9_.-]{0,199}") || value.endsWith(".") || value.matches("(?i)(CON|PRN|AUX|NUL|COM[1-9]|LPT[1-9])(?:\\..*)?")) throw new IOException("Unsupported component filename");
        return value;
    }
    public File link(String group, String name, File source) throws Exception {
        if (closed) throw new IOException("Engine workspace is closed"); check.run();
        if (group == null || !group.matches("[a-z][a-z0-9_]{0,31}")) throw new IOException("Invalid component group");
        filename(name);
        String identity = (group + "/" + name).toLowerCase(Locale.ROOT);
        if (names.contains(identity)) throw new IOException("Duplicate component execution filename");
        Path original = source.toPath();
        if (!Files.isRegularFile(original, LinkOption.NOFOLLOW_LINKS) || Files.isSymbolicLink(original)) throw new IOException("Selected asset is not a regular file");
        Path folder = directory.resolve(group);
        Files.createDirectories(folder);
        Path destination = folder.resolve(name);
        // BundleStore holds the lease until the worker has exited and these links have been removed.
        // A hardlink failure must not silently duplicate a multi-gigabyte model.
        Files.createLink(destination, original);
        names.add(identity);
        check.run(); return destination.toFile();
    }
    private static void remove(Path path) throws IOException {
        if (!Files.exists(path, LinkOption.NOFOLLOW_LINKS)) return;
        Path boundary = path.toAbsolutePath().normalize();
        Files.walkFileTree(path, EnumSet.noneOf(FileVisitOption.class), 4, new SimpleFileVisitor<Path>() {
            @Override public FileVisitResult preVisitDirectory(Path dir, BasicFileAttributes attrs) throws IOException {
                if (!dir.toRealPath().startsWith(boundary)) throw new IOException("Refusing to traverse a workspace alias");
                return FileVisitResult.CONTINUE;
            }
            @Override public FileVisitResult visitFile(Path file, BasicFileAttributes attrs) throws IOException {
                // walkFileTree does not follow symbolic links; delete their entries, never their targets.
                if (attrs.isDirectory()) throw new IOException("Workspace nesting exceeds application bounds");
                Files.delete(file); return FileVisitResult.CONTINUE;
            }
            @Override public FileVisitResult postVisitDirectory(Path dir, IOException error) throws IOException {
                if (error != null) throw error; Files.delete(dir); return FileVisitResult.CONTINUE;
            }
        });
    }
    /** Call once on Application startup before any workers are launched. */
    public static void recover(File root) throws IOException {
        Path parent = root(root);
        try (DirectoryStream<Path> entries = Files.newDirectoryStream(parent)) {
            int count = 0;
            for (Path entry : entries) {
                if (++count > 1024 || !entry.getFileName().toString().matches("work-[a-f0-9-]{36}")) throw new IOException("Unexpected engine workspace entry; preserved for inspection");
                remove(entry);
            }
        }
    }
    @Override public void close() throws IOException {
        if (!closed) { remove(directory); closed = true; }
    }
}
