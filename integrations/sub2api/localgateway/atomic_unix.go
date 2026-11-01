//go:build !windows

package localgateway

import "os"

func replaceFile(from, to string) error { return os.Rename(from, to) }
