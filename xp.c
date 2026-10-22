// Minimal Mach-service reachability probe.
// Reads one service name per line on stdin, writes "name<TAB>reply-description".
#include <xpc/xpc.h>
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
            continue;
        }
        xpc_connection_set_event_handler(c, ^(xpc_object_t ev) { (void)ev; });
        xpc_connection_resume(c);
        xpc_object_t msg = xpc_dictionary_create(NULL, NULL, 0);
        xpc_object_t rep = xpc_connection_send_message_with_reply_sync(c, msg);
        if (!rep) {
            printf("%s\t<null-reply>\n", line);
        } else {
            char *d = xpc_copy_description(rep);
            printf("%s\t%s\n", line, d ? d : "<null-desc>");
            free(d);
            xpc_release(rep);
        }
        xpc_release(msg);
        xpc_release(c);
        fflush(stdout);
    }
    return 0;
}
