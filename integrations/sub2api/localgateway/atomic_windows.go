//go:build windows

package localgateway

import (
	"syscall"
	"unsafe"
)

// Replace atomically with write-through; never delete the previous registry first.
func replaceFile(from, to string) error {
	source, e := syscall.UTF16PtrFromString(from)
	if e != nil {
		return e
	}
	target, e := syscall.UTF16PtrFromString(to)
	if e != nil {
		return e
	}
	result, _, err := syscall.NewLazyDLL("kernel32.dll").NewProc("MoveFileExW").Call(uintptr(unsafe.Pointer(source)), uintptr(unsafe.Pointer(target)), 0x1|0x8)
	if result == 0 {
		return err
	}
	return nil
}
