// Minimal Mach-service reachability probe with a per-service timeout.
// Reads one service name per line on stdin, writes "name<TAB>reply-description".
#include <xpc/xpc.h>
#include <dispatch/dispatch.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

int main(void) {
    char line[512];
    while (fgets(line, sizeof line, stdin)) {
        line[strcspn(line, "\n")] = 0;
        if (!line[0]) continue;
        xpc_connection_t c = xpc_connection_create_mach_service(line, NULL, 0);
        if (!c) {
            printf("%s\t<no-conn>\n", line);
            fflush(stdout);
            continue;
        }
        dispatch_semaphore_t sem = dispatch_semaphore_create(0);
        __block char *desc = NULL;
        xpc_connection_set_event_handler(c, ^(xpc_object_t ev) { (void)ev; });
        xpc_connection_resume(c);
        xpc_object_t msg = xpc_dictionary_create(NULL, NULL, 0);
        xpc_connection_send_message_with_reply(c, msg, NULL, ^(xpc_object_t rep) {
            if (rep) {
                desc = xpc_copy_description(rep);
            }
            dispatch_semaphore_signal(sem);
        });
        long timedout = dispatch_semaphore_wait(
            sem, dispatch_time(DISPATCH_TIME_NOW, 2ull * NSEC_PER_SEC));
        if (timedout != 0) {
            printf("%s\t<timeout>\n", line);
        } else {
            printf("%s\t%s\n", line, desc ? desc : "<null-reply>");
        }
        free(desc);
        // deliberately not releasing c/msg: a late reply must not touch freed objects
        fflush(stdout);
    }
    return 0;
}
