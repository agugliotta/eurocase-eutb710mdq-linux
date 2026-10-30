// SPDX-License-Identifier: GPL-2.0-or-later
#include <alsa/asoundlib.h>
#include <assert.h>
#include <errno.h>
#include <fcntl.h>
#include <linux/input.h>
#include <math.h>
#include <poll.h>
#include <signal.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/ioctl.h>
#include <sys/wait.h>
#include <unistd.h>

static volatile sig_atomic_t stopping;
static void stop(int sig) { (void)sig; stopping = 1; }
static int alsa_config(snd_config_t **cfg)
{
    const char *s = "ctl.poc { type hw card 0 } pcm.poc { type hw card 0 device 0 }";
    return snd_config_load_string(cfg, s, strlen(s));
}

static int controls(int tone)
{
    snd_config_t *cfg = NULL;
    snd_ctl_t *ctl = NULL;
    snd_pcm_t *pcm = NULL;
    snd_ctl_elem_list_t *list;
    snd_ctl_elem_info_t *info;
    snd_ctl_elem_value_t *value;
    snd_ctl_elem_id_t *id;
    snd_ctl_elem_list_alloca(&list);
    snd_ctl_elem_info_alloca(&info);
    snd_ctl_elem_value_alloca(&value);
    snd_ctl_elem_id_alloca(&id);
    snd_ctl_elem_value_t *saved[8] = {0};
    unsigned nsaved = 0, found = 0;
    int rc = alsa_config(&cfg);
    if (rc < 0) goto end;
    rc = snd_ctl_open_lconf(&ctl, "poc", 0, cfg);
    if (rc < 0) goto end;
    rc = snd_ctl_elem_list(ctl, list);
    if (rc < 0) goto end;
    unsigned total = snd_ctl_elem_list_get_count(list);
    if (total > 256) { rc = -EOVERFLOW; goto end; }
    rc = snd_ctl_elem_list_alloc_space(list, total);
    if (rc < 0) goto end;
    rc = snd_ctl_elem_list(ctl, list);
    if (rc < 0) goto free_list;
    for (unsigned i = 0; i < snd_ctl_elem_list_get_used(list); i++) {
        snd_ctl_elem_list_get_id(list, i, id);
        snd_ctl_elem_info_clear(info);
        snd_ctl_elem_info_set_id(info, id);
        rc = snd_ctl_elem_info(ctl, info);
        if (rc < 0) goto free_list;
        snd_ctl_elem_value_clear(value);
        snd_ctl_elem_value_set_id(value, id);
        rc = snd_ctl_elem_read(ctl, value);
        if (rc < 0) goto free_list;
        const char *name = snd_ctl_elem_id_get_name(id);
        unsigned count = snd_ctl_elem_info_get_count(info);
        snd_ctl_elem_type_t type = snd_ctl_elem_info_get_type(info);
        printf("CONTROL %s type=%d count=%u", name, type, count);
        if (type == SND_CTL_ELEM_TYPE_INTEGER)
            printf(" range=%ld:%ld", snd_ctl_elem_info_get_min(info), snd_ctl_elem_info_get_max(info));
        for (unsigned k = 0; k < count; k++) {
            if (type == SND_CTL_ELEM_TYPE_INTEGER) printf(" %ld", snd_ctl_elem_value_get_integer(value, k));
            if (type == SND_CTL_ELEM_TYPE_BOOLEAN) printf(" %d", snd_ctl_elem_value_get_boolean(value, k));
            if (type == SND_CTL_ELEM_TYPE_ENUMERATED) printf(" %u", snd_ctl_elem_value_get_enumerated(value, k));
        }
        puts("");
        if (!tone) continue;
        int bit = 0, desired = 0;
        if (!strcmp(name, "DAC Playback Volume") && type == SND_CTL_ELEM_TYPE_INTEGER) { bit = 1; desired = 63; }
        if (!strcmp(name, "Headphone Playback Volume") && type == SND_CTL_ELEM_TYPE_INTEGER) { bit = 2; desired = 53; }
        if (!strcmp(name, "Headphone Playback Switch") && type == SND_CTL_ELEM_TYPE_BOOLEAN) { bit = 4; desired = 1; }
        if (!strcmp(name, "Headphone Source Playback Route") && type == SND_CTL_ELEM_TYPE_ENUMERATED) { bit = 8; desired = 0; }
        if (!bit) continue;
        if (nsaved == 8) { rc = -EOVERFLOW; goto free_list; }
        if (type == SND_CTL_ELEM_TYPE_INTEGER &&
            (desired < snd_ctl_elem_info_get_min(info) || desired > snd_ctl_elem_info_get_max(info))) {
            rc = -ERANGE; goto free_list;
        }
        if (type == SND_CTL_ELEM_TYPE_ENUMERATED) {
            snd_ctl_elem_info_set_item(info, 0);
            rc = snd_ctl_elem_info(ctl, info);
            if (rc < 0 || strcmp(snd_ctl_elem_info_get_item_name(info), "DAC")) { rc = -EINVAL; goto free_list; }
        }
        rc = snd_ctl_elem_value_malloc(&saved[nsaved]);
        if (rc < 0) goto free_list;
        snd_ctl_elem_value_copy(saved[nsaved++], value);
        for (unsigned k = 0; k < count; k++) {
            if (type == SND_CTL_ELEM_TYPE_INTEGER) snd_ctl_elem_value_set_integer(value, k, desired);
            if (type == SND_CTL_ELEM_TYPE_BOOLEAN) snd_ctl_elem_value_set_boolean(value, k, desired);
            if (type == SND_CTL_ELEM_TYPE_ENUMERATED) snd_ctl_elem_value_set_enumerated(value, k, desired);
        }
        rc = snd_ctl_elem_write(ctl, value);
        if (rc < 0) goto free_list;
        found |= bit;
    }
    if (!tone) { rc = 0; goto free_list; }
    if (found != 15) { fprintf(stderr, "Required controls missing: mask=%u\n", found); rc = -ENOENT; goto free_list; }
    rc = snd_pcm_open_lconf(&pcm, "poc", SND_PCM_STREAM_PLAYBACK, SND_PCM_NONBLOCK, cfg);
    if (rc < 0) goto free_list;
    rc = snd_pcm_set_params(pcm, SND_PCM_FORMAT_S16_LE, SND_PCM_ACCESS_RW_INTERLEAVED, 2, 48000, 0, 100000);
    if (rc < 0) goto free_list;
    puts("TONE_START 440Hz 2s PCM_peak=-20dBFS HP=-10dB"); fflush(stdout);
    for (unsigned frame = 0; frame < 96000 && !stopping;) {
        short samples[960];
        unsigned n = 96000 - frame < 480 ? 96000 - frame : 480;
        for (unsigned i = 0; i < n; i++) {
            unsigned t = frame + i;
            double fade = fmin(1.0, fmin(t / 480.0, (95999-t) / 480.0));
            short sample = (short)(3276 * fade * sin(2 * M_PI * 440 * t / 48000.0));
            samples[i*2] = samples[i*2+1] = sample;
        }
        unsigned done = 0;
        while (done < n && !stopping) {
            snd_pcm_sframes_t written = snd_pcm_writei(pcm, samples + 2*done, n-done);
            if (written == -EAGAIN) {
                rc = snd_pcm_wait(pcm, 1000);
                if (rc <= 0) { rc = rc ? rc : -ETIMEDOUT; goto free_list; }
            } else if (written < 0) { rc = written; goto free_list; }
            else if (!written) { rc = -EIO; goto free_list; }
            else done += written;
        }
        frame += n;
    }
    snd_pcm_nonblock(pcm, 0);
    rc = stopping ? -EINTR : snd_pcm_drain(pcm);
    puts("TONE_END");
free_list:
    snd_ctl_elem_list_free_space(list);
end:
    if (pcm) { snd_pcm_drop(pcm); snd_pcm_close(pcm); }
    int restore_error = 0;
    while (nsaved) {
        snd_ctl_elem_value_t *v = saved[--nsaved];
        int r = snd_ctl_elem_write(ctl, v);
        if (r < 0) restore_error = r;
        snd_ctl_elem_value_free(v);
    }
    if (tone) printf("CONTROLS_RESTORED=%d\n", !restore_error);
    if (ctl) snd_ctl_close(ctl);
    if (cfg) snd_config_delete(cfg);
    if (rc >= 0 && restore_error) rc = restore_error;
    if (rc < 0) fprintf(stderr, "ALSA: %s\n", snd_strerror(rc));
    return rc < 0 ? 1 : 0;
}

// Both ends of a fresh gesture must hit the same button.
static int power_hit(int which, int col, int row)
{
    if (row < 25 || row >= 31) return 0;
    if (which == 4) {
        if (col >= 5 && col < 59) return 5;
        if (col >= 68 && col < 122) return 6;
    }
    if ((which == 5 || which == 6) && col >= 5 && col < 59) return -which;
    return 0;
}

static int power_touch(int which, int start_col, int start_row, int col, int row)
{
    int hit = power_hit(which, col, row);
    return hit == power_hit(which, start_col, start_row) ? hit : 0;
}

static int request_power(int which)
{
    if (which != 5 && which != 6) return -EINVAL;
#ifdef PANEL_POWER_ACTIONS
    // Enable only after USB poweroff and kernel restart hardware validation.
    pid_t child = fork();
    if (child < 0) return -errno;
    if (!child) {
        execl(which == 5 ? "/sbin/poweroff" : "/sbin/reboot",
              which == 5 ? "poweroff" : "reboot", (char *)NULL);
        _exit(127);
    }
    int status;
    while (waitpid(child, &status, 0) < 0) {
        if (errno != EINTR) return -errno;
    }
    return WIFEXITED(status) && WEXITSTATUS(status) == 0 ? 0 : -EIO;
#else
    return -ENOTSUP;
#endif
}

static FILE *screen;
static void power_button(int col, const char *label)
{
    for (int r=25; r<31; r++)
        fprintf(screen,"\033[%d;%dH\033[44m%54s\033[0m",r,col,"");
    fprintf(screen,"\033[27;%dH\033[1;44m%s\033[0m",col+4,label);
}

static void text(int row, int col, const char *s)
{ fprintf(screen, "\033[%d;%dH%s", row, col, s); }
static void page(int which)
{
    fputs("\033[0m\033[2J\033[H\033[?25l", screen);
#ifdef PANEL_SD_BOOT
    text(2, 5, "LINUX NATIVO / EUROCASE A23 / POC MICROSD");
    text(4, 5, "Raiz de solo lectura. HOME vuelve al menu.");
#else
    text(2, 5, "LINUX NATIVO / EUROCASE A23 / POC EN RAM");
    text(4, 5, "Sin instalar en almacenamiento. HOME vuelve al menu.");
#endif
    if (!which) {
        const char *labels[] = {"COLORES", "TACTIL", "AUDIO: TONO SUAVE", "SISTEMA"};
        for (int i=0; i<4; i++) {
            int row = 8 + (i/2)*12, col = 5 + (i%2)*63;
            for (int r=0; r<8; r++) {
                fprintf(screen,"\033[%d;%dH\033[%dm%54s\033[0m",row+r,col,44+i,"");
            }
            fprintf(screen,"\033[%d;%dH\033[1;%dm%s\033[0m",row+3,col+4,44+i,labels[i]);
        }
        text(33, 5, "Toca un boton grande y levanta el dedo.");
    } else if (which == 1) {
        const int colors[]={7,3,6,2,5,1,4,0};
        for (int i=0;i<8;i++) for (int r=9;r<29;r++)
            fprintf(screen,"\033[%d;%dH\033[%dm%16s",r,i*16+1,40+colors[i],"");
        fputs("\033[0m",screen);
    } else if (which == 2) {
        text(6,5,"Cruz = contacto aproximado. Escala Y provisional para este POC.");
    } else if (which == 4) {
        text(9,5,"Linux 6.12 / ARMv7 A23 / dos CPU / 1 GiB reconocido");
        text(12,5,"LCD 1024x600: texto y colores confirmados");
        text(15,5,"Power + Home + acelerometro: eventos confirmados");
        text(18,5,"Wi-Fi: recepcion pasiva confirmada; sin asociacion");
        text(21,5,"Tactil aproximado. Camaras y suspension fuera de alcance.");
        power_button(5,"APAGAR");
        power_button(68,"REINICIAR");
    } else if (which == 5 || which == 6) {
        text(9,5,which == 5 ? "APAGAR ESTA TABLET?" : "REINICIAR ESTA TABLET?");
        text(12,5,"HOME cancela y vuelve al menu.");
#ifndef PANEL_POWER_ACTIONS
        text(16,5,"PRUEBA: acciones bloqueadas hasta validar energia.");
#endif
        power_button(5,"CONFIRMAR");
    } else if (which == 7) {
        text(9,5,"Accion enviada al sistema. Espera...");
    }
    fflush(screen);
}

static int ui(void)
{
    struct pollfd fds[3];
    const char *names[] = {"axp20x-pek", "1c22800.lradc", "silead_ts"};
    for (int i=0;i<3;i++) fds[i]=(struct pollfd){.fd=-1,.events=POLLIN};
    int rc = 1;
    for (int i=0;i<3;i++) {
        char path[64], name[128]={0};
        snprintf(path,sizeof(path),"/dev/input/event%d",i);
        fds[i].fd=open(path,O_RDONLY|O_NONBLOCK);
        if (fds[i].fd<0 || ioctl(fds[i].fd,EVIOCGNAME(sizeof(name)),name)<0 || strcmp(name,names[i])) {
            fprintf(stderr,"Unexpected input %s: %s\n",path,name); goto end;
        }
    }
    screen=fopen("/dev/tty0","w");
    if (!screen) goto end;
    int which=0, x=0, y=0, release=0, oldrow=0, oldcol=0;
    int pressed=0, start_page=-1, start_col=0, start_row=0, power_sent=0;
    page(0); printf("POC_UI_READY pid=%ld\n",(long)getpid()); fflush(stdout);
    while (!stopping) {
        int n=poll(fds,3,500);
        if (n<0) { if(errno==EINTR) continue; goto end; }
        for (int i=0;i<3;i++) {
            if(fds[i].revents&(POLLERR|POLLHUP|POLLNVAL)) goto end;
            struct input_event e;
            while (read(fds[i].fd,&e,sizeof(e))==sizeof(e)) {
                if(i==1 && e.type==EV_KEY && e.code==KEY_HOME && e.value==0) { which=0;pressed=0;release=0;start_page=-1;page(0); }
                if(i==0 && e.type==EV_KEY && e.code==KEY_POWER) {
                    text(35,5,e.value?"POWER: pulsado ":"POWER: soltado ");fflush(screen);
                }
                if(i!=2) continue;
                if(e.type==EV_ABS && e.code==ABS_MT_POSITION_X) x=e.value;
                if(e.type==EV_ABS && e.code==ABS_MT_POSITION_Y) y=e.value;
                if(e.type==EV_KEY && e.code==BTN_TOUCH && e.value==1) pressed=1;
                if(e.type==EV_KEY && e.code==BTN_TOUCH && e.value==0) release=1;
                if(e.type!=EV_SYN || e.code!=SYN_REPORT) continue;
                // shortcut: Y/650 is approximate; replace only for a calibrated product.
                int col=x<0?1:x>=1024?128:x*128/1024+1;
                int row=y<0?1:y>=650?37:y*37/650+1;
                if (pressed) {
                    start_page=which;start_col=col;start_row=row;pressed=0;
                }
                if(which==2) {
                    if(oldrow) text(oldrow,oldcol," ");
                    text(row,col,"+");oldrow=row;oldcol=col;
                    fprintf(screen,"\033[34;5HContacto raw X=%4d Y=%4d     ",x,y);fflush(screen);
                }
                if(release) {
                    printf("TOUCH_RELEASE x=%d y=%d page=%d\n",x,y,which);fflush(stdout);
                    release=0;
                    int target = !power_sent && start_page == which ? power_touch(which,start_col,start_row,col,row) : 0;
                    start_page=-1;
                    if (target > 0) { which=target;page(which); }
                    else if (target < 0) {
                        int power_rc=request_power(which);
                        printf("POWER_REQUEST action=%s result=%d\n",which==5?"poweroff":"reboot",power_rc);
                        if (!power_rc) { power_sent=1;which=7; }
                        page(which);
                        text(33,5,power_rc == -ENOTSUP ? "Prueba OK: ninguna accion ejecutada. HOME para salir." :
                             power_rc ? "Error al solicitar la accion. Ver log USB; HOME para salir." :
                                        "Accion solicitada a init. Espera...");
                        fflush(screen);
                    }
                    else if(which==0 && col>=5 && col<122 && row>=8 && row<28 && !(col>=59&&col<68) && !(row>=16&&row<20)) {
                        which=1+(row>=20?2:0)+(col>=68?1:0);page(which);oldrow=0;
                        if(which==3) {
                            text(12,5,"Tono 440 Hz / 2 segundos / nivel bajo");fflush(screen);
                            int sound_rc=controls(1);
                            text(16,5,sound_rc?"Audio: error; ver log USB":"PCM completado. Confirmar sonido con el usuario.");fflush(screen);
                        }
                    }
                }
            }
        }
    }
    rc=0;
end:
    if(screen){fputs("\033[0m\033[?25h\033[37;1H",screen);fclose(screen);}
    for(int i=0;i<3;i++) if(fds[i].fd>=0)close(fds[i].fd);
    return rc;
}

int main(int argc,char **argv)
{
    setvbuf(stdout,NULL,_IOLBF,0);
    signal(SIGINT,stop);signal(SIGTERM,stop);
    if(argc!=2)return 2;
    if(!strcmp(argv[1],"--audio-info"))return controls(0);
    if(!strcmp(argv[1],"--tone"))return controls(1);
    if(!strcmp(argv[1],"--ui"))return ui();
    if(!strcmp(argv[1],"--self-check")) {
        assert(1023*128/1024+1==128);assert(645*37/650+1==37);
        for (int which=4; which<=6; which++) {
            int hit = which == 4 ? 5 : -which;
            assert(power_touch(which,5,25,58,30)==hit);
            assert(power_touch(which,5,25,59,30)==0);
            assert(power_touch(which,4,25,5,25)==0);
            assert(power_touch(which,5,24,5,25)==0);
            assert(power_touch(which,5,25,5,31)==0);
        }
        assert(power_touch(4,68,25,121,30)==6);
        assert(power_touch(4,5,25,68,25)==0);
        assert(power_hit(0,5,25)==0);assert(power_hit(7,5,25)==0);
        assert(power_hit(5,68,25)==0);
#ifndef PANEL_POWER_ACTIONS
        assert(request_power(5)==-ENOTSUP);assert(request_power(6)==-ENOTSUP);
#endif
        assert(request_power(0)==-EINVAL);
        snd_config_t *cfg=NULL;assert(alsa_config(&cfg)>=0);snd_config_delete(cfg);
        puts("POC_SELF_CHECK_OK");return 0;
    }
    return 2;
}
