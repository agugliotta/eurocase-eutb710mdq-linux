#include <errno.h>
#include <fcntl.h>
#include <linux/input.h>
#include <poll.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/ioctl.h>
#include <time.h>
#include <unistd.h>

int main(int argc, char **argv)
{
    _Static_assert(sizeof(struct input_event) == 16, "Expected ARM32 input ABI");
    if (argc != 3 || strncmp(argv[1], "/dev/input/event", 16))
        return 2;
    char *end;
    long seconds = strtol(argv[2], &end, 10);
    if (*end || seconds < 1 || seconds > 300)
        return 2;
    int fd = open(argv[1], O_RDONLY | O_NONBLOCK);
    if (fd < 0) { perror("open input"); return 1; }
    char name[256] = {0};
    if (ioctl(fd, EVIOCGNAME(sizeof(name)), name) < 0) {
        perror("input name"); close(fd); return 1;
    }
    setvbuf(stdout, NULL, _IOLBF, 0);
    printf("INPUT_NAME=%s\n", name);
    struct input_absinfo axis;
    if (!ioctl(fd, EVIOCGABS(ABS_MT_POSITION_X), &axis))
        printf("ABS_MT_X_RANGE=%d:%d\n", axis.minimum, axis.maximum);
    if (!ioctl(fd, EVIOCGABS(ABS_MT_POSITION_Y), &axis))
        printf("ABS_MT_Y_RANGE=%d:%d\n", axis.minimum, axis.maximum);
    struct timespec now;
    clock_gettime(CLOCK_MONOTONIC, &now);
    time_t deadline = now.tv_sec + seconds;
    struct pollfd p = { .fd = fd, .events = POLLIN };
    unsigned count = 0;
    while (count < 8192) {
        clock_gettime(CLOCK_MONOTONIC, &now);
        if (now.tv_sec >= deadline) break;
        int ready = poll(&p, 1, 250);
        if (ready < 0 && errno == EINTR) continue;
        if (ready < 0 || p.revents & (POLLERR | POLLHUP | POLLNVAL)) {
            fprintf(stderr, "input poll failed\n"); close(fd); return 1;
        }
        struct input_event ev;
        if (ready && read(fd, &ev, sizeof(ev)) == sizeof(ev)) {
            printf("type=%u code=%u value=%d\n", ev.type, ev.code, ev.value);
            count++;
        }
    }
    printf("INPUT_RECORDS=%u\n", count);
    close(fd);
    return 0;
}
